
IMAGE_NAME=envoy-extproc-sdk
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
	PYTHONPATH=.:$(GENERATED_CODE) DD_TRACE_ENABLED=false \
		poetry run python -m pytest -v tests/unit \
		--capture no

.PHONY: mock-test
mock-test: 
	PYTHONPATH=.:$(GENERATED_CODE) DD_TRACE_ENABLED=false \
		poetry run python tests/integration/mocked_app.py

.PHONY: run
run:
	poetry run python -m envoy_extproc_sdk --service $(SERVICE)

.PHONY: build
build:
	docker build . -t $(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: package
package:
	poetry build

.PHONY: publish
publish:
	poetry publish -r pypi --build