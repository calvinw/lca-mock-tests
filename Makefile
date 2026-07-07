CASE_STUDIES := $(notdir $(wildcard case_studies/*))
RUN := uv run python

.PHONY: build release check clean all all-build all-release all-check all-clean

# Usage: make build CASE=mock_widget
build:
	$(RUN) case_studies/$(CASE)/build.py

release:
	$(RUN) scripts/make_release.py case_studies/$(CASE)

check:
	$(RUN) scripts/check_case_study.py case_studies/$(CASE)

clean:
	rm -rf case_studies/$(CASE)/.bw_project case_studies/$(CASE)/_extracted case_studies/$(CASE)/mock_lca.zip

# Build + release + check every case study
all: all-build all-release all-check

all-build:
	@for cs in $(CASE_STUDIES); do \
		echo "=== build $$cs ==="; \
		$(RUN) case_studies/$$cs/build.py || exit 1; \
	done

all-release:
	@for cs in $(CASE_STUDIES); do \
		echo "=== release $$cs ==="; \
		$(RUN) scripts/make_release.py case_studies/$$cs || exit 1; \
	done

all-check:
	@for cs in $(CASE_STUDIES); do \
		echo "=== check $$cs ==="; \
		$(RUN) scripts/check_case_study.py case_studies/$$cs || exit 1; \
	done

all-clean:
	@for cs in $(CASE_STUDIES); do \
		rm -rf case_studies/$$cs/.bw_project case_studies/$$cs/_extracted case_studies/$$cs/mock_lca.zip; \
	done
