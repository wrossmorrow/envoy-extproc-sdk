# DecoratedExtProcService
#
# This example shows how to use the decorator pattern, common
# in python networking frameworks, to implement a processor.
# All the other examples use the subclass pattern, and actually
# this is just a copy of DigestExtProcService and should behave
# exactly the same.
#
# In the decorator pattern, we define a BaseExtProcService, ideally
# passing it a name so it is identifiable, and decorate the phase
# processing methods we wish to use. The decoration returns the
# decorated method of course, but more importantly serves to
# "register" the method being decorated as the appropriate handler
# for a specific phase. The decorated function must only match the
# type/signature of a handler to work.

from typing import Dict

from envoy_extproc_sdk import BaseExtProcService, ext_api, serve
from grpc import ServicerContext

from .digest import digest_headers

REQUEST_DIGEST_HEADER = "x-request-digest"
TENANT_ID_HEADER = "x-tenant-id"

DecoratedExtProcService = BaseExtProcService(name="DecoratedExtProcService")


@DecoratedExtProcService.process("request_headers")
def start_digest(
    headers: ext_api.HttpHeaders,
    context: ServicerContext,
    request: Dict,
    response: ext_api.HeadersResponse,
) -> ext_api.HeadersResponse:
    request["tenant"] = BaseExtProcService.get_header(headers, TENANT_ID_HEADER)
    if not request["tenant"]:
        request["tenant"] = "unknown"
    request["digest"] = digest_headers(headers, request)
    if request["method"].lower() == "get":
        digest = request["digest"].hexdigest()
        BaseExtProcService.add_header(response.response, REQUEST_DIGEST_HEADER, digest)
    return response


@DecoratedExtProcService.process("request_body")
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


if __name__ == "__main__":

    import logging

    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])

    serve(service=DecoratedExtProcService())
