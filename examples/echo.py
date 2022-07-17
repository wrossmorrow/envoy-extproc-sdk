# EchoExtProcService
#
# This example is a straightforward demonstration of
# how to _immediately_ respond from an ExternalProcessor
# without actually hitting the upstream service. Specifically,
# if there is a "truthy" `x-echo-only` header in the request
# then this processor will send an echo response back when
# it receives the request body. It does this by raising the
# StopRequestProcessing exception, which isn't necessarily
# an "error" but rather a signal of the need to stop request
# processing.

import re
from typing import Dict

from envoy_extproc_sdk import (
    BaseExtProcService,
    ext_api,
    serve,
    StopRequestProcessing,
)
from envoy_extproc_sdk.util.envoy import EnvoyHttpStatusCode
from grpc import ServicerContext

TRUTHY_REGEX = re.compile(r"^([Tt](rue)?|[Yy](es)?)$")


class EchoExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:
        request["request_headers"] = {}
        for header in [h for h in headers.headers.headers if h.key[0] != ":"]:
            request["request_headers"][header.key] = header.value
        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.CommonResponse,
    ) -> ext_api.CommonResponse:

        if "x-echo-only" not in request["request_headers"]:
            return response

        match = TRUTHY_REGEX.match(request["request_headers"]["x-echo-only"])
        if not match:
            return response

        response = self.form_immediate_response(
            EnvoyHttpStatusCode.OK, request["request_headers"], body.body
        )
        raise StopRequestProcessing(response=response)


if __name__ == "__main__":

    import logging

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=EchoExtProcService())
