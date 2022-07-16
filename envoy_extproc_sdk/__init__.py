# from ddtrace import patch_all

# patch_all()

# from .health import FilterOutHealthChecks  # noqa: E402
# tracer.configure(settings={"FILTERS": [FilterOutHealthChecks()]})

from .extproc import BaseExtProcService  # noqa: F401,E402
from .extproc import StopRequestProcessing  # noqa: F401,E402
from .server import create_server, serve  # noqa: F401,E402
from .util.envoy import ext_api  # noqa: F401,E402
