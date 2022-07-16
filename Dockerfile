# syntax=docker/dockerfile:1.2
FROM python:3.9-slim

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends curl python3-dev gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -y clean

# https://github.com/grpc-ecosystem/grpc-health-probe/#example-grpc-health-checking-on-kubernetes
RUN GRPC_HEALTH_PROBE_VER=v0.3.1 \
    && GRPC_HEALTH_PROBE_URL=https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VER}/grpc_health_probe-linux-amd64 \
    && curl ${GRPC_HEALTH_PROBE_URL} -L -s -o /bin/grpc_health_probe \
    && chmod +x /bin/grpc_health_probe

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/etc/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.1.13

ENV POETRY_PATH="${POETRY_HOME}/bin/poetry"

WORKDIR /envoy_extproc_sdk

# https://python-poetry.org/docs/master/#installation
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN cd /usr/local/bin && ln -s ${POETRY_PATH} && chmod +x ${POETRY_PATH}

COPY ./poetry.lock ./pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install -vvv --no-dev --no-root

COPY ./envoy_extproc_sdk ./envoy_extproc_sdk
COPY ./examples ./examples
COPY generated/python/standardproto/ ./

ARG GRPC_PORT=50051
EXPOSE ${GRPC_PORT}

ENTRYPOINT ["python","-m","envoy_extproc_sdk"]
