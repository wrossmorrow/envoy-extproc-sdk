import logging
import re
from typing import Dict

from envoy_extproc_sdk import (
    BaseExtProcService,
    ext_api,
    serve,
    StopRequestProcessing,
)
from envoy_extproc_sdk.util.envoy import (
    EnvoyHeaderValue,
    EnvoyHeaderValueOption,
    EnvoyHttpStatus,
    EnvoyHttpStatusCode,
)
from grpc import ServicerContext

TRUTHY_REGEX = re.compile(r"^([Tt](rue)?|[Yy](es)?)$")


class EchoExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:
        request["request_headers"] = {}
        for header in [h for h in headers.headers.headers if h.key[0] != ":"]:
            request["request_headers"][header.key] = header.value
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:

        if "x-echo-only" not in request["request_headers"]:
            return response

        match = TRUTHY_REGEX.match(request["request_headers"]["x-echo-only"])
        if not match:
            return response

        response = ext_api.ImmediateResponse(
            status=EnvoyHttpStatus(code=EnvoyHttpStatusCode.OK),
            body=body.body,
        )
        response.headers.set_headers.extend(
            [
                EnvoyHeaderValueOption(header=EnvoyHeaderValue(key=key, value=value))
                for key, value in request["request_headers"].items()
            ]
        )
        raise StopRequestProcessing(response=response)


if __name__ == "__main__":

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=EchoExtProcService())
