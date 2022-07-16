import logging
from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

EXTRA_REQUEST_ID_HEADER = "X-Extra-Request-Id"


class TrivialExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        self.add_header(
            response.response,
            EXTRA_REQUEST_ID_HEADER,
            request["__id"],
        )
        return response

    def process_response_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> Union[ext_api.HeadersResponse, ext_api.ImmediateResponse]:
        self.add_header(
            response.response,
            EXTRA_REQUEST_ID_HEADER,
            request["__id"],
        )
        return response


if __name__ == "__main__":

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=TrivialExtProcService())
