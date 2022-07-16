# DigestExtProcService
#
# This ExternalProcessor demonstrates some inter-phase action
# on both request headers and body. We compute a SHA256 digest
# of certain headers and any sent request body, and send the
# hex form of that digest to upstreams and back to the caller
# via a header `x-request-digest`. This is another example of
# storing an _object_ in the request context, like the timer
# service TimerExtProcService.

from hashlib import sha256
from typing import Any, Dict

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

REQUEST_DIGEST_HEADER = "x-request-digest"
TENANT_ID_HEADER = "x-tenant-id"


def digest_headers(headers: ext_api.HttpHeaders, request: Dict) -> Any:
    digest = sha256()
    digest.update(request["tenant"].encode())
    digest.update(request["method"].encode())
    digest.update(request["path"].encode())
    return digest


class DigestExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:

        request["tenant"] = self.get_header(headers, TENANT_ID_HEADER)
        if not request["tenant"]:
            request["tenant"] = "unknown"

        request["digest"] = digest_headers(headers, request)

        # GETs don't have bodies? May not see request body phase
        if request["method"].lower() == "get":
            digest = request["digest"].hexdigest()
            self.add_header(response.response, REQUEST_DIGEST_HEADER, digest)
            request["encoded"] = digest

        return response

    def process_request_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:

        request["digest"].update(body.body)
        digest = request["digest"].hexdigest()
        self.add_header(response.response, REQUEST_DIGEST_HEADER, digest)
        request["encoded"] = digest

        return response

    def process_response_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:

        digest = request["encoded"]
        self.add_header(response.response, REQUEST_DIGEST_HEADER, digest)
        return response


if __name__ == "__main__":

    import logging

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=DigestExtProcService())
