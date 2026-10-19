-include .env
export

ORG ?= leith_community_sports

.PHONY: setup db test lint demo dbt-build score clean

setup:          ## Install everything into the active virtualenv
	pip install -e ".[dev,load,dbt]"

db:             ## Start Postgres and wait until it is healthy
	docker compose up -d --wait db

test:           ## Unit tests, including a DuckDB end-to-end load (no Postgres needed)
	pytest

lint:
	ruff check . && ruff format --check .

demo: db        ## Generate the synthetic charity, load it, build and test every model
	funderready demo
	cd dbt && DBT_PROFILES_DIR=. dbt build --vars '{org: $(ORG)}'

score:          ## How many planted problems the data-quality inbox found
	python scripts/score_inbox.py data/demo/planted_errors.json $(ORG)

clean:
	docker compose down -v
	rm -rf data dbt/target dbt/logs
