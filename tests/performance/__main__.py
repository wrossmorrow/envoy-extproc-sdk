from typing import Tuple

from envoy_extproc_sdk.util.timer import Timer
import requests

HOST = "localhost"
PORT = 8080

COUNT = 1000


def run_requests(N: int, method: str, url: str) -> Timer:
    with Timer() as T:
        for n in range(N):
            requests.request(method, url)
    return T


def run_compare(N: int, host: str, port: int, method: str, path: str) -> Tuple[Timer, Timer]:
    T = run_requests(N, method, f"http://{host}:{port}/no-ext-procs/{path}")
    S = run_requests(N, method, f"http://{host}:{port}/{path}")
    return T, S


T, S = run_compare(COUNT, HOST, PORT, "get", "something")

print(f"without extprocs: {T.duration_ns() * 1.0e-9} s, {T.duration_ns()/COUNT * 1e-6} ms/req")
print(f"   with extprocs: {S.duration_ns() * 1.0e-9} s, {S.duration_ns()/COUNT * 1e-6} ms/req")
print(f"extproc overhead: {(S.duration_ns()-T.duration_ns())/COUNT * 1e-6} ms/req")
