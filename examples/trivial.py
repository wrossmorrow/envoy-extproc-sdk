from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api
from grpc import ServicerContext


class TrivialExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        callctx["request_id"] = self.get_header(headers, "x-request-id")
        response = self.just_continue_headers()
        self.add_header(
            response.response,
            "X-Extra-Request-Id",
            callctx["request_id"],
        )
        return response

    def process_response_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        response = self.just_continue_headers()
        self.add_header(
            response.response,
            "X-Extra-Request-Id",
            callctx["request_id"],
        )
        return response
