# syntax=docker/dockerfile:1.2
FROM python:3.9-slim

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends curl python3-dev gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -y clean

WORKDIR app

COPY echo.py ./

ENTRYPOINT ["python"]
CMD ["echo.py"]
