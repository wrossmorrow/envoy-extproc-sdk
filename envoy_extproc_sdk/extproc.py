from __future__ import annotations

from asyncio import CancelledError, iscoroutinefunction
from distutils.util import strtobool as tobool
from enum import Enum
from logging import getLogger
from os import environ
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union

from ddtrace import tracer  # noqa: F401
from grpc import ServicerContext, StatusCode

from .util.envoy import (
    EnvoyExtProcServicer,
    EnvoyHeaderValue,
    EnvoyHeaderValueOption,
    ext_api,
)
from .util.timer import Timer

logger = getLogger(__name__)


REVEAL_EXTPROC_CHAIN = tobool(environ.get("REVEAL_EXTPROC_CHAIN", "True"))
EXTPROCS_APPLIED_HEADER_NAME = "x-ext-procs-applied"
ENVOY_SERVICE_NAME = "envoy.service.ext_proc.v3.ExternalProcessor"

ExtProcHandler = Callable


class ExtProcPhase(str, Enum):
    request_headers = "request_headers"
    request_body = "request_body"
    request_trailers = "request_trailers"
    response_headers = "response_headers"
    response_body = "response_body"
    response_trailers = "response_trailers"


class StopRequestProcessing(Exception):
    def __init__(self, response: ext_api.ImmediateResponse, reason: Optional[str] = None) -> None:
        self.response = response
        self.reason = reason


class BaseExtProcService(EnvoyExtProcServicer):
    """
    Base ExternalProcessor for envoy. Subclass this and supply
    more specific action methods if desired. Or use the @process
    decorator to add handlers for specific phases.
    """

    STANDARD_REQUEST_HEADERS = {
        ":method": "method",
        ":path": "path",
        "content-type": "content_type",
        "x-request-id": "__id",
    }
    STANDARD_RESPONSE_HEADERS = {
        "content-type": "content_type",
        "content-length": "content_length",
    }

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.__class__.__name__

    def __repr__(self) -> str:
        """Get this object's \"name\", either class name or overriden"""
        return self.name

    def __call__(self) -> BaseExtProcService:
        """This no-op makes symbol importing and decorating work together"""
        return self

    async def Process(
        self,
        request_iterator: Iterator[ext_api.ProcessingRequest],
        context: ServicerContext,
    ) -> Iterator[ext_api.ProcessingResponse]:
        """
        Basic stream handler. This creates a "local" ("request") context
        for each request and walks through the request iterator
        calling (implemented) phase-specific methods for each
        HTTP request phase envoy sends data for. Implement those
        "process_..." methods in subclasses to assert behavior.

        The local/call context ("request") is _particularly_ important
        in envoy because the stream will only get data in each phase
        that is immediately relevant to that phase; headers gets headers,
        body gets body. So if a processor needs headers to process
        a body, we have to store that in the header phase.

        Note that this is _not_ usefully cachable for concurrency, as
        we have no way to universally key across request phases. That is,
        the request_headers phase could create a context and cache it
        by the x-request-id, but no later phase will know that key.
        Given envoy's processing model we have to maintain this object
        in-memory for a given stream with Process.

        Also defines some helpers like get_header (to get a request
        header in a header phase) and add/remove_header for changing
        headers.
        """

        with tracer.trace(
            "process",
            resource=f"/{ENVOY_SERVICE_NAME}/Process",
            span_type="grpc",
        ):

            # for each stream invocation, define a new "call" context/"request"
            request = {"__overhead_ns": 0, "__phase": "unknown", "__id": "unknown"}

            async for req in self.safe_iterator(request_iterator, context, request):

                phase = req.WhichOneof("request")
                request["__phase"] = phase

                # get the request-phase's data
                data = getattr(req, phase)

                # get the "action" to apply
                action_name = f"process_{phase}"
                action = getattr(self, action_name, None)

                if phase == "request_headers":
                    request.update(self.get_standard_request_headers(data))
                elif phase == "response_headers":
                    request.update(self.get_standard_response_headers(data))

                if (action is None) or (not callable(action)):
                    msg = f"{self.name} does not implement a callable for {phase}"
                    logger.error(msg)
                    context.abort(StatusCode.UNIMPLEMENTED, msg)

                # get a response object to pass (convenience)
                response = getattr(self, f"get_{phase}_response")()

                # NOTE: this only applies if we process response_headers...
                # that's an envoy configuration. To always capture this we
                # could assert that the response headers ProcessingMode is
                # always SEND
                if REVEAL_EXTPROC_CHAIN and (phase == "response_headers"):
                    response = self.add_extprocs_chain_header(data, response)

                # actually process the phase, wrapped for timing and tracing
                try:
                    response = await self.process_phase(
                        phase, data, context, request, response, action
                    )
                    yield ext_api.ProcessingResponse(**{phase: response})
                except StopRequestProcessing as err:
                    logger.debug(
                        "caught StopRequestProcessing, sending ImmediateResponse",
                        extra={
                            "processor": self.name,
                            "phase": request.get("__phase", "unknown"),
                            "request": request.get("__id", "unknown"),
                            "reason": err.reason or "none supplied",
                        },
                    )
                    yield ext_api.ProcessingResponse(immediate_response=err.response)

    async def safe_iterator(
        self,
        request_iterator: Iterator[ext_api.ProcessingRequest],
        context: ServicerContext,
        request: Dict,
    ) -> Iterator[ext_api.ProcessingResponse]:
        try:
            async for req in request_iterator:
                yield req
        except CancelledError:
            logger.debug(
                "RPC cancelled by client",
                extra={
                    "processor": self.name,
                    "phase": request.get("__phase", "unknown"),
                    "request": request.get("__id", "unknown"),
                },
            )
            return

    async def process_phase(
        self,
        phase: str,
        data: Union[ext_api.HttpHeaders, ext_api.HttpBody, ext_api.HttpTrailers],
        context: ServicerContext,
        request: Dict,
        response: Union[ext_api.HeadersResponse, ext_api.BodyResponse, ext_api.TrailersResponse],
        action: Callable,
    ) -> Optional[
        Union[
            ext_api.HeadersResponse,
            ext_api.BodyResponse,
            ext_api.TrailersResponse,
            ext_api.ImmediateResponse,
        ]
    ]:

        # actually process the request phase
        logger.debug(
            f"{self.name} started {phase}",
            extra={
                "processor": self.name,
                "phase": request.get("__phase", "unknown"),
                "request": request.get("__id", "unknown"),
            },
        )

        T = Timer().tic()

        camel_case_phase = "".join([w.title() for w in phase.split("_")])
        resource_name = f"/{ENVOY_SERVICE_NAME}/Process/{camel_case_phase}"
        with tracer.trace(f"process.{phase}", resource=resource_name, span_type="grpc"):
            if iscoroutinefunction(action):
                response = await action(data, context, request, response)
            else:
                response = action(data, context, request, response)

        T.toc()
        duration = T.duration().ToNanoseconds()
        request["__overhead_ns"] += duration

        # how to store the data in the headers for chaining?
        # write events to kafka? Automatically impose headers?

        logger.debug(
            f"{self.name} finished {phase}",
            extra={
                "processor": self.name,
                "phase": request.get("__phase", "unknown"),
                "request": request.get("__id", "unknown"),
                "duration_ns": duration,
            },
        )

        return response

    # decorator-based assignment; use as
    #
    #   P = BaseExtProcService(name="MyExtProc")
    #
    #   @P.processor("request_headers")
    #   async def some_func(headers, context, request):
    #       ...
    #

    def processor(self, phase: ExtProcPhase) -> Callable:
        def wrapper(func: ExtProcHandler) -> ExtProcHandler:
            setattr(self, f"process_{phase}", func)
            return getattr(self, f"process_{phase}")

        return wrapper

    # phase-specific methods below here; override to
    # specialize filter behavior, these will simply move on

    async def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:
        return response

    async def process_request_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:
        return response

    async def process_request_trailers(
        self,
        trailers: ext_api.HttpTrailers,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.TrailersResponse,
    ) -> ext_api.TrailersResponse:
        return response

    async def process_response_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:
        return response

    async def process_response_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:
        return response

    async def process_response_trailers(
        self,
        trailers: ext_api.HttpTrailers,
        grpcctx: ServicerContext,
        request: Dict,
        response: ext_api.TrailersResponse,
    ) -> ext_api.TrailersResponse:
        return response

    # some boilerplate; not really encapsulating anything but
    # possibly useful methods

    def just_continue_response(self) -> ext_api.CommonResponse:
        """generic "move on" response object (can be modified)"""
        return ext_api.CommonResponse(
            status=ext_api.CommonResponse.ResponseStatus.CONTINUE,
            header_mutation=ext_api.HeaderMutation(
                set_headers=[],
                remove_headers=[],
            ),
        )

    def just_continue_headers(self) -> ext_api.HeadersResponse:
        """generic "move on" headers response object (can be modified)"""
        return ext_api.HeadersResponse(response=self.just_continue_response())

    def just_continue_body(self) -> ext_api.BodyResponse:
        """generic "move on" body response object (can be modified)"""
        return ext_api.BodyResponse(response=self.just_continue_response())

    def just_continue_trailers(self) -> ext_api.TrailersResponse:
        """generic "move on" trailers response object (can be modified)"""
        return ext_api.TrailersResponse(header_mutation=ext_api.HeaderMutation())

    def get_request_headers_response(self) -> ext_api.HeadersResponse:
        return self.just_continue_headers()

    def get_response_headers_response(self) -> ext_api.HeadersResponse:
        return self.just_continue_headers()

    def get_request_body_response(self) -> ext_api.BodyResponse:
        return self.just_continue_body()

    def get_response_body_response(self) -> ext_api.BodyResponse:
        return self.just_continue_body()

    def get_request_trailers_response(self) -> ext_api.TrailersResponse:
        return self.just_continue_trailers()

    def get_response_trailers_response(self) -> ext_api.TrailersResponse:
        return self.just_continue_trailers()

    # helpers

    @staticmethod
    def get_header(headers: ext_api.HttpHeaders, name: str, lower_cased: bool = False) -> str:
        """get a header value by name (envoy uses lower cased names)"""
        _name = name if lower_cased else name.lower()
        for header in headers.headers.headers:
            if header.key == _name:
                return header.value
        return None

    @staticmethod
    def get_headers(
        headers: ext_api.HttpHeaders,
        names: Union[List[str], Dict[str, str]],
        lower_cased: bool = False,
        mapping: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """get multiple header values by name (envoy uses lower cased names)"""

        if isinstance(names, list):  # enforce dictionary input
            keys = dict(zip(names, mapping)) if mapping else {n: n for n in names}
            return BaseExtProcService.get_headers(headers, keys, lower_cased=lower_cased)

        if not lower_cased:  # enforce lower-cased keys
            keys = {k.lower(): v for k, v in names.items()}
            return BaseExtProcService.get_headers(headers, keys, lower_cased=True)

        results = {name: None for _, name in names.items()}  # initialize to None
        for header in headers.headers.headers:
            if header.key in names:
                results[names[header.key]] = header.value  # store value at mapped name
        return results

    @staticmethod
    def add_header(
        response: ext_api.CommonResponse, key: str, value: str
    ) -> ext_api.CommonResponse:
        """add a header to a CommonResponse"""
        header = EnvoyHeaderValue(key=key, value=value)
        response.header_mutation.set_headers.append(EnvoyHeaderValueOption(header=header))
        return response

    @staticmethod
    def add_headers(
        response: ext_api.CommonResponse,
        headers: Union[Dict[str, str], List[Tuple[str, str]]],
    ) -> ext_api.CommonResponse:
        """add a set of headers to a CommonResponse"""
        if isinstance(headers, dict):
            return BaseExtProcService.add_headers(response, [(k, v) for k, v in headers.items()])
        response.header_mutation.set_headers.extend(
            [
                EnvoyHeaderValueOption(header=EnvoyHeaderValue(key=key, value=value))
                for key, value in headers
            ]
        )
        return response

    @staticmethod
    def remove_header(response: ext_api.CommonResponse, name: str) -> ext_api.CommonResponse:
        """remove a header from a CommonResponse"""
        response.header_mutation.remove_headers.append(name)
        return response

    @staticmethod
    def remove_headers(
        response: ext_api.CommonResponse, names: List[str]
    ) -> ext_api.CommonResponse:
        """remove a header from a CommonResponse"""
        response.header_mutation.remove_headers.extend(names)
        return response

    @staticmethod
    def get_standard_request_headers(headers: ext_api.HttpHeaders) -> Dict[str, str]:
        """pull a chosen set of "standard" HTTP headers from envoy headers"""
        return BaseExtProcService.get_headers(
            headers,
            names=BaseExtProcService.STANDARD_REQUEST_HEADERS,
            lower_cased=True,
        )

    @staticmethod
    def get_standard_response_headers(headers: ext_api.HttpHeaders) -> Dict[str, str]:
        """pull a chosen set of "standard" HTTP headers from envoy headers"""
        return BaseExtProcService.get_headers(
            headers,
            names=BaseExtProcService.STANDARD_RESPONSE_HEADERS,
            lower_cased=True,
        )

    def add_extprocs_chain_header(
        self,
        headers: ext_api.HttpHeaders,
        response: Union[ext_api.HeadersResponse, ext_api.ImmediateResponse],
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        """
        This function helps provide visibility into the customized filter chain.
        Not a helper, this should stay in the base processor logic.
        """

        header: EnvoyHeaderValue

        filters_header = self.get_header(headers, EXTPROCS_APPLIED_HEADER_NAME, lower_cased=True)
        if filters_header:
            header = EnvoyHeaderValue(
                key=EXTPROCS_APPLIED_HEADER_NAME,
                value=f"{self.name},{filters_header}",
            )
        else:
            header = EnvoyHeaderValue(key=EXTPROCS_APPLIED_HEADER_NAME, value=f"{self.name}")

        if isinstance(response, ext_api.ImmediateResponse):
            response.headers.set_headers.append(EnvoyHeaderValueOption(header=header))
        else:
            response.response.header_mutation.set_headers.append(
                EnvoyHeaderValueOption(header=header)
            )

        return response