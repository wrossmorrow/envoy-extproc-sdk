from typing import Dict

from envoy_extproc_sdk import BaseExtProcService, ext_api
from envoy_extproc_sdk.util.timer import Timer
from grpc import ServicerContext

REQUEST_STARTED_HEADER = "X-Request-Started"
REQUEST_DURATION_HEADER = "X-Duration-Ns"


class TimingExtProcService(BaseExtProcService):
    """ "Global" request timer that provides request timing for
    any upstream filters (or services) as well as a duration
    (over upstreams) response header"""

    def process_request_headers(
        self,
        headers: ext_api.HttpHeaders,
        context: ServicerContext,
        request: Dict,
        response: ext_api.HeadersResponse,
    ) -> ext_api.HeadersResponse:
        """Start a timer in the context, add a request started header"""
        request["timer"] = Timer().tic()
        response = self.just_continue_headers()
        self.add_header(response.response, REQUEST_STARTED_HEADER, request["timer"].started_iso())
        return response

    def process_response_body(
        self,
        body: ext_api.HttpBody,
        context: ServicerContext,
        request: Dict,
        response: ext_api.BodyResponse,
    ) -> ext_api.BodyResponse:
        """ "End" the timer in the context, add a response duration header"""
        timer = request["timer"].toc()
        response = self.just_continue_body()
        self.add_header(response.response, REQUEST_STARTED_HEADER, timer.started_iso())
        self.add_header(response.response, REQUEST_DURATION_HEADER, str(timer.duration_ns()))
        return response
