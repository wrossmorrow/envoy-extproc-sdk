import argparse
from importlib import import_module
import logging
from os import environ

from .extproc import BaseExtProcService
from .server import serve
from .settings import GRPC_PORT, SHUTDOWN_GRACE_PERIOD

logger = logging.getLogger(__name__)

# Coroutines to be invoked when the event loop is shutting down.
_cleanup = []


def import_from_spec(spec: str) -> BaseExtProcService:
    module_spec = ".".join(spec.split(".")[:-1])
    symbol_name = spec.split(".")[-1]
    module = import_module(module_spec)
    if hasattr(module, symbol_name):
        return getattr(module, symbol_name)
    raise AttributeError(f"{module_spec} has no attribute {symbol_name}")


def parse_cli_args() -> argparse.Namespace:
    """
    parse arguments. import paths can be used for --service, as in

        python -m envoy_extproc_sdk run \
            --service app.SomeExtProcService

    when this SDK is imported. This way, no implementing service
    needs to, by itself, implement a __main__.py function with
    boilerplate.
    """

    parser: argparse.ArgumentParser = argparse.ArgumentParser()

    parser.add_argument(
        "-s",
        "--service",
        dest="service",
        required=False,
        type=str,
        default=None,
        help="Processor to use, as an import spec",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        required=False,
        type=int,
        default=GRPC_PORT,
        help="Port to run service on",
    )
    parser.add_argument(
        "-g",
        "--grace-period",
        dest="grace_period",
        required=False,
        type=int,
        default=SHUTDOWN_GRACE_PERIOD,
        help="Grace period to finish requests on shutdown",
    )
    parser.add_argument(
        "-l",
        "--logging",
        dest="logging",
        default=False,
        action="store_true",
        help="Include logging setup",
    )

    args: argparse.Namespace = parser.parse_args()

    return args


if __name__ == "__main__":  # pragma: no cover

    args = parse_cli_args()

    if args.logging:
        LOG_LEVEL = environ.get("LOG_LEVEL", "INFO").upper()
        FORMAT = "%(asctime)s : %(levelname)s : %(message)s"
        logging.basicConfig(level=LOG_LEVEL, format=FORMAT, handlers=[logging.StreamHandler()])

    service = import_from_spec(args.service)() if args.service else BaseExtProcService()
    serve(service, args.port, args.grace_period)
