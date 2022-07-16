# # type: ignore
# from typing import List, Optional

# from ddtrace import Span
# from ddtrace.filters import TraceFilter
# import grpc
# from grpclib.health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse

# grpc_health_path_base = "grpc.health"  # allow extension to future versions
# grpc_health_path_v1 = f"{grpc_health_path_base}.v1.Health"


# class FilterOutHealthChecks(TraceFilter):
#     def exclude(self, span: Span):
#         """
#         return True if span_type == grpc and resource starts with /{grpc_health_path_base}
#         """
#         return (span.span_type == "grpc") and span.resource.startswith(f"/{grpc_health_path_base}")

#     def include(self, span: Span):
#         return not self.exclude(span)

#     def process_trace(self, trace: List[Span]) -> Optional[List[Span]]:
#         for span in trace:
#             if self.exclude(span):
#                 return None
#         return trace


# class CustomHealthService:
#     async def Check(
#         self, request: HealthCheckRequest, context: grpc.ServicerContext
#     ) -> HealthCheckResponse:
#         return HealthCheckResponse(status=HealthCheckResponse.ServingStatus.SERVING)


# def register_health(server: grpc.Server) -> None:

#     health = CustomHealthService()
#     v1_handler = grpc.method_handlers_generic_handler(
#         grpc_health_path_v1,
#         {
#             "Check": grpc.unary_unary_rpc_method_handler(
#                 health.Check,
#                 request_deserializer=HealthCheckRequest.FromString,
#                 response_serializer=HealthCheckResponse.SerializeToString,
#             ),
#         },
#     )
#     server.add_generic_rpc_handlers((v1_handler,))
