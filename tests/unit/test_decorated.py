import re
from uuid import uuid4

from envoy_extproc_sdk import ext_api
from envoy_extproc_sdk.testing import (
    AsEnvoyExtProc,
    envoy_body,
    envoy_headers,
    envoy_set_headers_to_dict,
)
from examples import DecoratedExtProcService
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers, body",
    (
        (
            envoy_headers(
                headers=[
                    (":method", "get"),
                    (":path", "/api/v0/resource"),
                    ("x-tenant-id", str(uuid4())),
                ]
            ),
            envoy_body(),
        ),
        (
            envoy_headers(
                headers=[
                    (":method", "get"),
                    (":path", "/api/v0/resource"),
                    ("x-tenant-id", str(uuid4())),
                ]
            ),
            envoy_body(),
        ),
        (
            envoy_headers(
                headers=[
                    (":method", "post"),
                    (":path", "/api/v0/resource"),
                    ("x-tenant-id", str(uuid4())),
                ]
            ),
            envoy_body(body="something"),
        ),
    ),
)
async def test_digester_flow(headers: ext_api.HttpHeaders, body: ext_api.HttpBody) -> None:

    E = AsEnvoyExtProc(request_headers=headers, request_body=body)
    P = DecoratedExtProcService

    method = P.get_header(headers, ":method")

    async for response in P.Process(E, None):

        if response.WhichOneof("response") == "request_headers":
            assert isinstance(response.request_headers, ext_api.HeadersResponse)
            _response = response.request_headers.response
            _headers = envoy_set_headers_to_dict(_response)
            assert _response.status == 0
            # if method is get, should have a header
            if method == "get":
                assert _headers
                assert "x-request-digest" in _headers
                assert re.match(r"^[0-9a-f]{64}$", _headers["x-request-digest"]) is not None

        elif response.WhichOneof("response") == "request_body":
            assert isinstance(response.request_body, ext_api.BodyResponse)
            _response = response.request_body.response
            _headers = envoy_set_headers_to_dict(_response)
            assert _response.status == 0
            # if method is not get, should have a header
            if method != "get":
                assert _headers
                assert "x-request-digest" in _headers
                assert re.match(r"^[0-9a-f]{64}$", _headers["x-request-digest"]) is not None
