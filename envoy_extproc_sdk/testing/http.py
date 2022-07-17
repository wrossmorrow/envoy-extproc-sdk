from json import dumps
from typing import Dict, List, Tuple, Union

from ..util.envoy import EnvoyHeaderMap, EnvoyHeaderValue, ext_api


def envoy_headers(
    headers: Union[Dict[str, str], List[Tuple[str, str]]] = None
) -> ext_api.HttpHeaders:
    """Create envoy-typed headers from a list of key-value-pair tuples"""
    if not headers:
        return ext_api.HttpHeaders()
    if isinstance(headers, list):
        return envoy_headers(dict(headers))
    if isinstance(headers, dict):
        return ext_api.HttpHeaders(
            headers=EnvoyHeaderMap(
                headers=[EnvoyHeaderValue(key=key, value=value) for key, value in headers.items()]
            )
        )
    raise ValueError(f"Unparseable headers type {type(headers)}")


def envoy_body(body: Union[bytes, int, str, list, dict] = None) -> ext_api.HttpBody:
    """Create envoy-typed body from several types"""
    if body is None:
        return ext_api.HttpBody()
    if isinstance(body, bytes):
        return ext_api.HttpBody(body=body)
    if isinstance(body, int):
        return ext_api.HttpBody(body=str(body).encode())
    if isinstance(body, str):
        return ext_api.HttpBody(body=body.encode())
    if isinstance(body, list) or isinstance(body, dict):
        return ext_api.HttpBody(body=dumps(body).encode())
    raise ValueError(f"Unparseable body type {type(body)}")


def envoy_set_headers_to_dict(response: ext_api.CommonResponse) -> Dict[str, str]:
    headers = {}
    for header_option in response.header_mutation.set_headers:
        headers[header_option.header.key] = header_option.header.value
    return headers
