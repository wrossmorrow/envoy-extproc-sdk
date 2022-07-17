# An Envoy ExternalProcessor SDK in python

## Overview

[`envoy`](https://www.envoyproxy.io/), one of the most powerful and widely used reverse proxies, is able to query an [ExternalProcessor](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_proc_filter) gRPC service in it's filter chain. This functionality opens the door to quickly and robustly implemently customized functions at the edge, instead of in targeted services. [Bond](www.bond.tech), for example, is using this functionality to implement authentication, API call logging, and write-request idempotency. While powerful, implementing these services still requires dealing with complicated `envoy` specs, managing information sharing across request phases, and an understanding of gRPC, none of which are exactly straightforward. 

**The purpose of this SDK is to make development of ExternalProcessors easy**. 

Specifically we supply a `BaseExtProcService` that provides much of the boilerplate required to make this type of service. Here is a brief, untyped example of how to build one (based on `examples/decorated.py`):
```
import logging
from envoy_extproc_sdk import BaseExtProcService, serve

DecoratedExtProcService = BaseExtProcService(name="DecoratedExtProcService")

@DecoratedExtProcService.process("request_headers")
def start_digest(headers, context, request, response):
    ... # do stuff

@DecoratedExtProcService.process("request_body")
def complete_digest(body, context, request, response):
    ... # do stuff

if __name__ == "__main__":
    FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler()])
    serve(service=DecoratedExtProcService())
```
In short, you can simple "decorate" methods (of the right signature) and get an ExternalProcessor. This "route decoration" is a pattern common to `python` server frameworks, and is probably the easiest way to get started. The primary pattern we use though is subclassing, as you'll see if you review `examples/*.py`. The `serve` interface adopts the `grpc.aio` paradigm, which we've found a bit cleaner to use here than the threading concurrency model. 

Really you'll still need to learn some details about how `envoy` specifies and types these services and their data, but it's much more limited here. Basically `BaseExtProcService` implements the single RPC `Process` [defined by the spec](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto), pulls out the request phase data from `ProcessingRequest`, and wraps request phase specific handlers in the requisite `ProcessingResponse`. This enables a subclass (or decorated methods) to focus solely on the logic for handling the request phases. These phases are
* `{request,response}_headers`: process request or response headers
* `{request,response}_body`: process request or response bodies
* `{request,response}_trailers`: process request or response trailers (note: we've found this buggy in `envoy`)

The `BaseExtProcService` _also_ implements it's own "request context" (the `request` argument in the decorated handlers above) to enable data passing between request phases. This is a _critical_ feature for effective, powerful external processing. `envoy` sends only request header data when asking to process request headers, only body data when asking to process request body, etc. But processor behaviors or computing can easily depend on the full known scope of request data. Storing and managing that data is what `request` is for; see `examples/*.py` for, well, exampled. 

We distribute this as `python` package and as a `docker` container. We do _not_ package generated code from `envoy`'s `protobuf` specs. So if you use the `python` package you have to build and install the `protobuf` generated code from `envoy` (see `buf.yaml` here). However you can build on top of the `envoy_extproc_sdk` `docker` image and avoid this, as we package the generated code in images. 

Of course, this service isn't useful outside an `envoy` deployment configured to use it. See `envoy.yaml` for example configurations. 

## Interface

### Utilities

Currently `BaseExtProcService` has some `staticmethod` helpers for processing headers. 

#### get_header

Get a header from the request or response headers. 

Arguments:
* `headers` an [HttpHeaders](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L180) object
* `name` (`str`) the name of the header to look for
* `lower_cased` (`bool`, default `False`) whether the name is _already_ lowercased

Returns the value of the header searched for, if it exists. `None` if it doesn't. 

#### get_headers

Get a set of headers from the request or response headers. 

Arguments:
* `headers` an [HttpHeaders](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L180) object
* `names` (`List[str]` or `Dict[str, str`) the names of the headers to look for, by _actual_ header names
* `lower_cased` (`bool`, default `False`) whether the name is _already_ lowercased
* `mapping` (`List[str]`) names to return if a list of `names` is supplied

Returns a `Dict` with mapped names as keys and header values (or `None`) as values.  

#### add_header

Add a header to the request or response headers. 

Arguments:
* `response` an [CommonResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L230) object
* `key` (`str`) the header to set
* `value` (`str`) the header value

Returns the updated response. 

#### add_headers

Add a set of headers to the request or response headers. 

Arguments:
* `response` an [CommonResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L230) object
* `headers` (`Union[Dict[str, str], List[Tuple[str, str]]]`) the headers, as a `dict` or list of key-value pairs, to add

Returns the updated response. 

#### remove_header

Remove a header from the request or response headers. 

Arguments:
* `response` an [CommonResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L230) object
* `name` (`str`) the header to remove (if it exists)

Returns the updated response. 

#### remove_headers

Remove a set of headers from the request or response headers.

Arguments:
* `response` an [CommonResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L230) object
* `name` (`List[str]`) the headers, by name, to remove (if they exist)

Returns the updated response. 


### Phase Handlers

The following documents how to implement the request phase handlers. In any phase you can `raise` a 
```
envoy_extproc_sdk.StopRequestProcessing
```
`Exception` to supply a response directly from the processor (without sending to the upstream processors or target). The constructor requires an [ImmediateResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L286) object, which you can construct with the helper method
```
    def form_immediate_response(
        status: EnvoyHttpStatusCode,
        headers: Dict[str, str],
        body: str,
    ) -> ext_api.ImmediateResponse:
```
in `BaseExtProcService`. 

#### `@P.process("request_headers")` or `def process_request_headers`

Arguments: 
* `headers`, an `envoy` [HttpHeaders](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L180) object describing the request headers. 
* `context`, a gRPC [ServicerContext](https://grpc.github.io/grpc/python/grpc.html#grpc.ServicerContext) from the RPC
* `request`, a simple `Dict` for supplying/supplementing request context across phases
* `response`, a [HeadersResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L213) object for telling `envoy` how to mutate the request (if at all). 

Return the (possibly modified) `response` passed in, or `raise` a `StopRequestProcessing`. 

#### `@P.process("request_body")` or `def process_request_body`

Arguments: 
* `body`, an `envoy` [HttpBody](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L199) object describing the request body. 
* `context`, a gRPC [ServicerContext](https://grpc.github.io/grpc/python/grpc.html#grpc.ServicerContext) from the RPC
* `request`, a simple `Dict` for supplying/supplementing request context across phases
* `response`, a [BodyResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L224) object for telling `envoy` how to mutate the request (if at all). 

Return the (possibly modified) `response` passed in, or `raise` a `StopRequestProcessing`. 

#### `@P.process("response_headers")` or `def process_response_headers`

Arguments: 
* `headers`, an `envoy` [HttpHeaders](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L180) object describing the request headers. 
* `context`, a gRPC [ServicerContext](https://grpc.github.io/grpc/python/grpc.html#grpc.ServicerContext) from the RPC
* `request`, a simple `Dict` for supplying/supplementing request context across phases
* `response`, a [HeadersResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L213) object for telling `envoy` how to mutate the response (if at all). 

Return the (possibly modified) `response` passed in, or `raise` a `StopRequestProcessing`. 

#### `@P.process("response_body")` or `def process_response_body`

Arguments: 
* `body`, an `envoy` [HttpBody](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L199) object describing the response body. 
* `context`, a gRPC [ServicerContext](https://grpc.github.io/grpc/python/grpc.html#grpc.ServicerContext) from the RPC
* `request`, a simple `Dict` for supplying/supplementing request context across phases
* `response`, a [BodyResponse](https://github.com/envoyproxy/envoy/blob/1cf5603dc5239c92e5bc38ef321f59ccf6eabc6e/api/envoy/service/ext_proc/v3/external_processor.proto#L224) object for telling `envoy` how to mutate the response (if at all). 

Return the (possibly modified) `response` passed in, or `raise` a `StopRequestProcessing`. 

#### Trailers

The trailers handlers are similar, but less likely to be used. See the code for details. 

## Examples

There are several examples in `examples/`. These are packaged in the `docker` image built from `Dockerfile`, and included as services in the `docker-compose.yaml`. The basic `envoy` config `envoy.yaml` (used by the `docker-compose`) sets each example up to be used

* `BaseExtProcService`: The `BaseExtProcService` is an example in it's own right, but does nothing to requests. Using `LOG_LEVEL=DEBUG` will print log lines describing the processing steps taken. Run with
```
LOG_LEVEL=DEBUG make run
```

* `TrivialExtProcService`: This example adds an upstream header as well as a response header, both the `x-request-id` but in the name `x-extra-request-id`. Run with
```
make run SERVICE=examples.TrivialExtProcService
```

* `TimerExtProcService`: This example times the request, add an upstream header (which the request started), and add two response headers (when the request started and how long it took in nanoseconds). Run with
```
make run SERVICE=examples.TrivialExtProcService
```

* `DigestExtProcService`: This example computes a SHA256 digest of the request method, path, and body, and add that as an upstream request header and a response header `x-request-digest`. It demonstrates inter-phase data use. Run with
```
make run SERVICE=examples.DigestExtProcService
```

* `DecoratedExtProcService`: This example copies `DigestExtProcService`, but implements the service using the `@process` decorator instead of as a subclass service. Run with
```
make run SERVICE=examples.DecoratedExtProcService
```

* `EchoExtProcService`: This example demonstrates use of `StopRequestProcessing` to respond immediately from an ExternalProcessor, instead of sending a request to the upstream processors or target. Run with
```
make run SERVICE=examples.EchoExtProcService
```

* `CtxExtProcService`: This example allows for testing the request context. It reads a request header `x-context-id`, adding that to the upstream request headers. If that header is missing, the service does nothing else. If it exists, it will also analyze the request body, which it expects to be exactly the `x-context-id` supplied. The processor will fail if this doesn't match. The filter also processes the response body, which it expects to be JSON with the request path equal to `path` (as with our echo server in `tests/mocks/echo`). The service checks that value matches the `path` stored in the request context. These steps are largely to check that we can _concurrently_ make requests with different values and see consistency in the response header `x-context-id`, which we will not get if the service's processing fails. Run with
```
make run SERVICE=examples.CtxExtProcService
```

## Development

### Requirements

* `python3.9`
* `poetry` for package management
* `make` for convenience commands
* `protoc` and `buf` for generating code from `protobuf` schemas for `envoy`
* `docker` for testing

### Quickstart

The `Makefile` provides a lot of helpful targets to get started. The simplest quickstart is probably
```
$ make install format unit-test run
```
This will (a) install the `python` dependencies, (b) use `buf` to generate code (and install it in the current virtual environment), (c) format the code, (d) run the unit tests, (e) and run the `BaseExtProcService`. However, running the service on it's own is only partially useful as the service is a gRPC service which isn't the easiest to just `curl` at. 

Review the `Makefile` for other commands, including 
* `format` (`isort`, `black`, and `flake8` linting), 
* `types` (for `mypy` static type analysis), 
* `build` (for `docker build`)
* `package` (for building a `python` package)
* `publish` (for distributing the `python` package)

The `docker-compose` is a setup with `envoy`, a naive "echo" HTTP server, and the example ExternalProcessor services from `examples/`. This way you can make plain HTTP requests and actually see outcomes from the filters. For example, after running 
```
$ docker-compose up --build
```
you can try 
```
$ curl localhost:8080/something -D -
HTTP/1.1 200 OK
server: envoy
date: Sat, 16 Jul 2022 22:55:19 GMT
content-length: 524
content-type: application/json
x-envoy-upstream-service-time: 1
x-request-started: 2022-07-16T22:55:19.290822Z
x-duration-ns: 23589000
x-ext-procs-applied: TrivialExtProcService,TimerExtProcService,EchoExtProcService,DigestExtProcService,DecoratedExtProcService,CtxExtProcService
x-extra-request-id: 554c54e8-fac1-42e3-8ab8-1f2264f59664

{"method": "get", "path": "/something", "headers": {"host": "localhost:8080", "user-agent": "curl/7.64.1", "accept": "*/*", "x-forwarded-proto": "http", "x-request-id": "554c54e8-fac1-42e3-8ab8-1f2264f59664", "x-extra-request-id": "554c54e8-fac1-42e3-8ab8-1f2264f59664", "x-request-started": "2022-07-16T22:55:19.290822Z", "x-request-digest": "860d64d6465b9e9886050295087e8a547b3e7a3c40e79d26147b50a97b9ac2c6", "x-context-id": "", "x-envoy-expected-rq-timeout-ms": "15000"}, "body": "{\"hello\":\"hi\"}", "message": "Hello"}
```
or 
```
$ curl localhost:8080/something -X PUT -H 'Content-type: application/json' -d '{"hello":"hi"}' -D -
HTTP/1.1 200 OK
server: envoy
date: Sat, 16 Jul 2022 22:54:49 GMT
content-length: 584
content-type: application/json
x-envoy-upstream-service-time: 0
x-request-digest: a794dbc467285567e4c2604c991938386366f6ab94b0b0e4fab5e27e0a932e60
x-request-started: 2022-07-16T22:54:49.660908Z
x-duration-ns: 25046000
x-ext-procs-applied: TrivialExtProcService,TimerExtProcService,EchoExtProcService,DigestExtProcService,DecoratedExtProcService,CtxExtProcService
x-extra-request-id: 7a983b59-d67c-44c8-a54a-2afae7069ac9

{"method": "put", "path": "/something", "headers": {"host": "localhost:8080", "user-agent": "curl/7.64.1", "accept": "*/*", "content-type": "application/json", "content-length": "14", "x-forwarded-proto": "http", "x-request-id": "7a983b59-d67c-44c8-a54a-2afae7069ac9", "x-extra-request-id": "7a983b59-d67c-44c8-a54a-2afae7069ac9", "x-request-started": "2022-07-16T22:54:49.660908Z", "x-request-digest": "a794dbc467285567e4c2604c991938386366f6ab94b0b0e4fab5e27e0a932e60", "x-context-id": "", "x-envoy-expected-rq-timeout-ms": "15000"}, "body": "{\"hello\":\"hi\"}", "message": "Hello"}
```

For contrast, here are these two requests _without_ filters: 
```
$ curl localhost:8080/something -X PUT -H 'Content-type: application/json' -d '{"hello":"hi"}' -D -
HTTP/1.1 200 OK
server: envoy
date: Sat, 16 Jul 2022 23:40:24 GMT
content-length: 362
content-type: application/json
x-envoy-upstream-service-time: 1

{"method": "put", "path": "/something", "headers": {"host": "localhost:8080", "user-agent": "curl/7.64.1", "accept": "*/*", "content-type": "application/json", "content-length": "14", "x-forwarded-proto": "http", "x-request-id": "0afcd2c4-6d3d-4513-a29b-40c7954f8942", "x-envoy-expected-rq-timeout-ms": "15000"}, "body": "{\"hello\":\"hi\"

$ curl localhost:8080/something -D -
HTTP/1.1 200 OK
server: envoy
date: Sat, 16 Jul 2022 23:40:30 GMT
content-length: 302
content-type: application/json
x-envoy-upstream-service-time: 1

{"method": "get", "path": "/something", "headers": {"host": "localhost:8080", "user-agent": "curl/7.64.1", "accept": "*/*", "x-forwarded-proto": "http", "x-request-id": "f8dfa254-157b-4f75-a7d0-121f3d245d6b", "x-envoy-expected-rq-timeout-ms": "15000"}, "body": "{\"hello\":\"hi\"}", "message": "Hello"}
```
Note the additional response headers and the extra information about the upstream services request headers in the response body. That's the filter set working! 