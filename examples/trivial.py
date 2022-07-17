# TrivialExtProcService
#
# This is our simplest example (outside of the BaseExtProcService
# itself). All this ExternalProcessor does is add another
# `x-request-id` header (with the same value) to both the
# upstream and back to the caller, as `x-extra-request-id`.

from typing import Dict, Union

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

EXTRA_REQUEST_ID_HEADER = "x-extra-request-id"


class TrivialExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:
        self.add_header(
            response,
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
    ) -> ext_api.CommonResponse:
        self.add_header(
            response,
            EXTRA_REQUEST_ID_HEADER,
            request["__id"],
        )
        return response


if __name__ == "__main__":

    import logging

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=TrivialExtProcService())
