from json import dumps
from typing import Any, Dict, List, Optional, Tuple, Union

from envoy_extproc_sdk import ext_api
from envoy_extproc_sdk.testing import (
    AsEnvoyExtProc,
    envoy_body,
    envoy_extproc_cycle,
    envoy_headers,
)
import pytest


@pytest.mark.parametrize(
    "headers",
    (
        None,
        {},
        [],
        {"some": "data"},
        [("some", "data")],
        {"some": "data", "more": "data"},
        [("some", "data"), ("more", "data")],
    ),
)
def test_envoy_headers(headers: Optional[Union[Dict[str, str], List[Tuple[str, str]]]]) -> None:
    h = envoy_headers(headers)
    assert isinstance(h, ext_api.HttpHeaders)


@pytest.mark.parametrize(
    "headers",
    (
        '{"some": "data"}',
        # 0, # technically falsey, returns an empty HttpHeaders object
        Union,
        ext_api.HttpHeaders(),
    ),
)
def test_bad_envoy_headers(headers: Any) -> None:
    with pytest.raises(ValueError):
        envoy_headers(headers)


@pytest.mark.parametrize(
    "body",
    (
        None,
        dumps({"some": "data"}).encode(),
        0,
        dumps({"some": "data"}),
        [{"some": "data"}],
        {"some": "data"},
    ),
)
def test_envoy_body(body: Optional[Union[bytes, int, str, list, dict]]) -> None:
    b = envoy_body(body)
    assert isinstance(b, ext_api.HttpBody)


@pytest.mark.parametrize(
    "body",
    (
        Union,
        ext_api.HttpHeaders(),
    ),
)
def test_bad_envoy_body(body: Any) -> None:
    with pytest.raises(ValueError):
        envoy_body(body)


@pytest.mark.asyncio
async def test_envoy_extproc_cycle() -> None:
    phases = {
        f"{r}_{t}": False for r in ["request", "response"] for t in ["headers", "body", "trailers"]
    }
    async for msg in envoy_extproc_cycle():
        assert isinstance(msg, ext_api.ProcessingRequest)
        phases[msg.WhichOneof("request")] = True
    assert all(v for k, v in phases.items())


@pytest.mark.asyncio
async def test_as_envoy() -> None:
    phases = {
        f"{r}_{t}": False for r in ["request", "response"] for t in ["headers", "body", "trailers"]
    }
    E = AsEnvoyExtProc()
    async for msg in E:
        assert isinstance(msg, ext_api.ProcessingRequest)
        phases[msg.WhichOneof("request")] = True
    assert all(v for k, v in phases.items())
