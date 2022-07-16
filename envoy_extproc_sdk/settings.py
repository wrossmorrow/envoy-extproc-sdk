from os import environ
import re

GRPC_PORT = int(environ.get("GRPC_PORT", "50051"))

SHUTDOWN_GRACE_PERIOD = int(environ.get("SHUTDOWN_GRACE_PERIOD", "5"))

REVEAL_EXTPROC_CHAIN = (
    re.match(r"^([Tt](rue)?|[Yy](es)?)$", environ.get("REVEAL_EXTPROC_CHAIN", "True")) is not None
)

EXTPROCS_APPLIED_HEADER = environ.get("EXTPROCS_APPLIED_HEADER", "x-ext-procs-applied")

ENVOY_SERVICE_NAME = "envoy.service.ext_proc.v3.ExternalProcessor"
