-include .env
export

ORG ?= leith_community_sports

.PHONY: setup db test lint demo score match holdout exercises clean

setup:          ## Install everything into the active virtualenv
	pip install -e ".[dev,load,dbt]"

db:             ## Start Postgres and wait until it is healthy (the dev container already has one)
	@if [ "$$PGHOST" = "db" ]; then echo "Using the dev container's Postgres"; \
	else docker compose up -d --wait db; fi

test:           ## Unit tests, including a DuckDB end-to-end load (no Postgres needed)
	pytest

lint:
	ruff check . && ruff format --check .

demo: db        ## Generate the synthetic charity, load it, build and test every model
	funderready demo
	cd dbt && DBT_PROFILES_DIR=. dbt build --vars '{org: $(ORG)}' --exclude tag:exercise

score:          ## How many planted problems the data-quality inbox found
	python scripts/score_inbox.py data/demo/planted_errors.json $(ORG)

match:          ## Duplicate resolution on the demo charity: threshold sweep, precision, recall
	python scripts/score_matching.py data/demo/truth.json:$(ORG)

HOLDOUT_SEEDS ?= 11 23 42
holdout: db     ## Check matching on charities the threshold was NOT tuned on
	for s in $(HOLDOUT_SEEDS); do \
	  funderready demo --seed $$s --org "Holdout $$s" --out data/holdout_$$s && \
	  (cd dbt && DBT_PROFILES_DIR=. dbt build -q --vars "{org: holdout_$$s}" --exclude tag:exercise) \
	  || exit 1; \
	done
	python scripts/score_matching.py data/demo/truth.json:$(ORG) \
	  $(foreach s,$(HOLDOUT_SEEDS),data/holdout_$(s)/truth.json:holdout_$(s))

exercises:      ## Your pair-build exercises: runs only their unit tests
	cd dbt && DBT_PROFILES_DIR=. dbt build --vars '{org: $(ORG)}' --select tag:exercise

clean:
	docker compose down -v
	rm -rf data dbt/target dbt/logs
