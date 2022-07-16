from asyncio import get_event_loop
from logging import getLogger
from os import environ

from grpc.aio import Server
from grpc.aio import server as grpc_aio_server

# from .health import register_health
from .extproc import BaseExtProcService
from .util.envoy import (
    add_ExternalProcessorServicer_to_server,
    EnvoyExtProcServicer,
)

logger = getLogger(__name__)

GRPC_PORT = int(environ.get("GRPC_PORT", "50051"))

SHUTDOWN_GRACE_PERIOD = int(environ.get("SHUTDOWN_GRACE_PERIOD", "5"))

# Coroutines to be invoked when the event loop is shutting down.
_cleanup = []


def create_server(
    service: EnvoyExtProcServicer = BaseExtProcService(), port: int = GRPC_PORT
) -> Server:
    server = grpc_aio_server()
    add_ExternalProcessorServicer_to_server(service, server)
    # register_health(server)
    server.add_insecure_port(f"[::]:{port}")
    return server


async def _serve(
    service: EnvoyExtProcServicer = BaseExtProcService(), port: int = GRPC_PORT
) -> None:
    server = create_server(service=service, port=port)
    logger.info(f'Starting Envoy ExternalProcessor "{service}" at {port}')
    await server.start()

    async def server_graceful_shutdown():
        logger.info("Starting graceful shutdown...")
        # Shuts down the server with 0 seconds of grace period. During the
        # grace period, the server won't accept new connections and allow
        # existing RPCs to continue within the grace period.
        await server.stop(SHUTDOWN_GRACE_PERIOD)

    _cleanup.append(server_graceful_shutdown())
    await server.wait_for_termination()


def serve(service: EnvoyExtProcServicer = BaseExtProcService(), port: int = GRPC_PORT) -> None:
    loop = get_event_loop()
    try:
        loop.run_until_complete(_serve(service=service, port=port))
    finally:
        loop.run_until_complete(*_cleanup)
        loop.close()
