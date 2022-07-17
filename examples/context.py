# CtxExtProcService
#
# TBD

from json import loads
from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

CONTEXT_ID_HEADER = "x-context-id"


class CtxExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:
        request["cid"] = self.get_header(headers, CONTEXT_ID_HEADER)
        self.add_header(response, CONTEXT_ID_HEADER, request["cid"])
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:
        if request.get("cid", None):
            cid = body.body.decode()
            assert cid == request["cid"]
        return response

    def process_response_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:
        if request.get("cid", None):
            data = loads(body.body.decode())
            path = data["path"]
            assert path == request["path"]
            self.add_header(response, CONTEXT_ID_HEADER, request["cid"])
        return response


if __name__ == "__main__":

    import logging

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=CtxExtProcService())
