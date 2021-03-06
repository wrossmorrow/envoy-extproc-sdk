
IMAGE_NAME=envoy-extproc-sdk-python
IMAGE_TAG=`git rev-parse HEAD`
GENERATED_CODE=generated/python/standardproto
SERVICE=envoy_extproc_sdk.BaseExtProcService

.PHONY: install
install: python-install codegen

.PHONY: update
update: python-update buf-update codegen

.PHONY: python-install
python-install:
	poetry install

.PHONY: python-update
python-update:
	poetry update

.PHONY: buf-update 
buf-update :
	buf mod update

.PHONY: codegen
codegen:
	bash scripts/remove_generated_code.sh
	buf -v generate buf.build/cncf/xds
	buf -v generate buf.build/envoyproxy/envoy
	buf -v generate buf.build/envoyproxy/protoc-gen-validate
	buf -v generate https://github.com/grpc/grpc.git --path src/proto/grpc/health/v1/health.proto
	bash scripts/fix_grpc_health_proto.sh
	bash scripts/install_generated_code.sh

.PHONY: format
format:
	poetry run isort envoy_extproc_sdk examples tests
	poetry run black envoy_extproc_sdk examples tests
	poetry run flake8 envoy_extproc_sdk examples tests

.PHONY: types
types:
	poetry run mypy envoy_extproc_sdk examples tests

.PHONY: lint
check-format:
	poetry run isort envoy_extproc_sdk examples tests --check
	poetry run black envoy_extproc_sdk examples tests --check
	poetry run flake8 envoy_extproc_sdk examples tests

.PHONY: unit-test
unit-test: 
	DD_TRACE_ENABLED=false \
		poetry run python -m pytest -v tests/unit

.PHONY: integration-test
integration-test: 
	DD_TRACE_ENABLED=false \
		poetry run python -m pytest tests/integration

.PHONY: coverage
coverage: 
	DD_TRACE_ENABLED=false \
		poetry run coverage run -m pytest -v tests/unit \
			--junitxml=test-results/junit.xml
	poetry run coverage report -m

.PHONY: run
run:
	poetry run python -m envoy_extproc_sdk --service $(SERVICE) --logging

.PHONY: build
build:
	docker build . -t $(IMAGE_NAME):$(IMAGE_TAG)
	docker build . -f examples/Dockerfile \
		--build-arg IMAGE_TAG=$(IMAGE_TAG) \
		-t $(IMAGE_NAME)-examples:$(IMAGE_TAG)

.PHONY: up
up:
	docker-compose up --build

.PHONY: down
down:
	docker-compose down --volumes

.PHONY: package
package:
	poetry build

.PHONY: publish
publish:
	poetry publish -r pypi --build
