from hashlib import sha256
from typing import Any, Dict

from envoy_extproc_sdk import BaseExtProcService, ext_api
from grpc import ServicerContext

REQUEST_DIGEST_HEADER = "x-request-digest"
TENANT_ID_HEADER = "x-tenant-id"


class DigestExtProcService(BaseExtProcService):
    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:

        request["digest"] = self.digest_headers(headers, request)

        # GETs don't have bodies? May not see request body phase
        if request["method"].lower() == "get":
            digest = request["digest"].hexdigest()
            self.add_header(response.response, REQUEST_DIGEST_HEADER, digest)

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

        return response

    def digest_headers(self, headers: ext_api.HttpHeaders, request: Dict) -> Any:

        request["tenant"] = self.get_header(headers, TENANT_ID_HEADER)

        digest = sha256()
        digest.update(request["tenant"].encode())
        digest.update(request["method"].encode())
        digest.update(request["path"].encode())
        return digest
