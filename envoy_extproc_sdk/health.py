from typing import List, Optional

from ddtrace import Span
from ddtrace.filters import TraceFilter
from grpc import ServicerContext
from grpc_health_check.v1.health_pb2 import (
    HealthCheckRequest,
    HealthCheckResponse,
)
from grpc_health_check.v1.health_pb2_grpc import (  # noqa: F401
    add_HealthServicer_to_server,
)
from grpc_health_check.v1.health_pb2_grpc import HealthServicer

grpc_health_path_base = "grpc.health"  # allow extension to future versions
grpc_health_path_v1 = f"{grpc_health_path_base}.v1.Health"


class FilterOutHealthChecks(TraceFilter):
    def exclude(self, span: Span):
        """
        return True if span_type == grpc and resource starts with /{grpc_health_path_base}
        """
        return (span.span_type == "grpc") and span.resource.startswith(f"/{grpc_health_path_base}")

    def include(self, span: Span):
        return not self.exclude(span)

    def process_trace(self, trace: List[Span]) -> Optional[List[Span]]:
        for span in trace:
            if self.exclude(span):
                return None
        return trace


class HealthService(HealthServicer):
    async def Check(
        self, request: HealthCheckRequest, context: ServicerContext
    ) -> HealthCheckResponse:
        return HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)
