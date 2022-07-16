from typing import Dict

from envoy_extproc_sdk import BaseExtProcService, StopRequestProcessing
from envoy_extproc_sdk.util.envoy import (
    EnvoyHeaderValue,
    EnvoyHeaderValueOption,
    EnvoyHttpStatus,
    EnvoyHttpStatusCode,
    ext_api,
)
from grpc import ServicerContext


class EchoExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        callctx: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:
        callctx["request_headers"] = {}
        response = self.just_continue_headers()
        for header in [h for h in headers.headers.headers if h.key[0] != ":"]:
            callctx["request_headers"][header.key] = header.value
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        callctx: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:
        response = ext_api.ImmediateResponse(
            status=EnvoyHttpStatus(code=EnvoyHttpStatusCode.OK),
            body=body.body,
        )
        response.headers.set_headers.extend(
            [
                EnvoyHeaderValueOption(header=EnvoyHeaderValue(key=key, value=value))
                for key, value in callctx["request_headers"].items()
            ]
        )
        raise StopRequestProcessing(response=response)
