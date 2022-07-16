from json import loads
from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api
from grpc import ServicerContext


class CtxExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:

        callctx["cid"] = self.get_header(headers, "x-custom-id")

        response = self.just_continue_headers()
        self.add_header(response.response, "X-Custom-Id", callctx["cid"])
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:

        cid = body.body.decode()
        assert cid == callctx["cid"]

        return self.just_continue_body()

    def process_response_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:

        data = loads(body.body.decode())
        path = data["path"]
        assert path == callctx["path"]

        response = self.just_continue_body()
        self.add_header(response.response, "X-Custom-Id", callctx["cid"])
        return response
