from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp


class Timer:
    """Simple timer object implementing the "with"
    interface for capturing start, end, and duration
    of a block of compute. Uses protobuf objects.
    """

    def __init__(self):
        self._start, self._end = Timestamp(), Timestamp()
        self._duration = Duration()
        self._running = False

    def __repr__(self) -> str:
        return f"{self.started_iso()}, {self.duration_ns()}"

    def __enter__(self):
        return self.tic()

    def __exit__(self, exc_type, exc_value, exc_trace):
        self.toc()
        self._duration.FromNanoseconds(self._end.ToNanoseconds() - self._start.ToNanoseconds())

    def tic(self):
        self._start.GetCurrentTime()
        self.running = True
        return self

    def toc(self):
        self._end.GetCurrentTime()
        self.running = False
        return self

    def started(self) -> Timestamp:
        return self._start

    def started_ns(self) -> int:
        return self.started().ToNanoseconds()

    def started_iso(self) -> str:
        return self.started().ToJsonString()

    def duration(self) -> Duration:
        self._duration.FromNanoseconds(self._end.ToNanoseconds() - self._start.ToNanoseconds())
        return self._duration

    def duration_ns(self) -> int:
        return self.duration().ToNanoseconds()
