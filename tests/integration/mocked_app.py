from logging import getLogger
from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

logger = getLogger(__name__)


class IntTestExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        response = self.just_continue_headers()
        self.add_header(response.response, "X-Bond-ExtProc-IntTest", "worked")
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        grpcctx: ServicerContext,
        callctx: Dict,
    ) -> Union[ext_api.BodyResponse, ext_api.ImmediateResponse]:
        response = self.just_continue_body()
        self.add_header(response.response, "X-Bond-ExtProc-IntTest", "worked")
        return response


if __name__ == "__main__":
    serve(service=IntTestExtProcService())
