from hashlib import sha256
import logging
from typing import Any, Dict

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

REQUEST_DIGEST_HEADER = "x-request-digest"
TENANT_ID_HEADER = "x-tenant-id"


DecoratedBaseExtProc = BaseExtProcService(name="DecoratedBaseExtProc")


@DecoratedBaseExtProc.processor("request_headers")
def start_digest(
    headers: ext_api.HttpHeaders,
    context: ServicerContext,
    request: Dict,
    response: ext_api.HeadersResponse,
) -> ext_api.HeadersResponse:

    request["digest"] = digest_headers(headers, request)

    # GETs don't have bodies? May not see request body phase
    if request["method"].lower() == "get":
        digest = request["digest"].hexdigest()
        BaseExtProcService.add_header(response.response, REQUEST_DIGEST_HEADER, digest)

    return response


@DecoratedBaseExtProc.processor("request_body")
def complete_digest(
    body: ext_api.HttpBody,
    context: ServicerContext,
    request: Dict,
    response: ext_api.BodyResponse,
) -> ext_api.BodyResponse:

    request["digest"].update(body.body)
    digest = request["digest"].hexdigest()
    BaseExtProcService.add_header(response.response, REQUEST_DIGEST_HEADER, digest)

    return response


def digest_headers(headers: ext_api.HttpHeaders, request: Dict) -> Any:
    request["tenant"] = BaseExtProcService.get_header(headers, TENANT_ID_HEADER)
    digest = sha256()
    digest.update(request["tenant"].encode())
    digest.update(request["method"].encode())
    digest.update(request["path"].encode())
    return digest


if __name__ == "__main__":

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=DecoratedBaseExtProc)
