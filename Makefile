CASE_STUDIES := $(notdir $(wildcard case_studies/*))
RUN := uv run python

.PHONY: build release check clean all all-build all-release all-check all-clean \
	bafu-build bafu-release bafu-prepare bafu-check bafu-clean openlca-check openlca-foreground \
	openlca-bafu

# Usage: make build CASE=cotton_fiber
build:
	$(RUN) case_studies/$(CASE)/build.py

release:
	$(RUN) scripts/make_release.py case_studies/$(CASE)

check:
	$(RUN) scripts/check_case_study.py case_studies/$(CASE)

clean:
	rm -rf case_studies/$(CASE)/.bw_project case_studies/$(CASE)/_extracted case_studies/$(CASE)/mock_lca.zip case_studies/$(CASE)/$(CASE).zip

bafu-build:
	$(RUN) bafu_case_studies/$(CASE)/build.py

bafu-release:
	$(RUN) scripts/make_release.py bafu_case_studies/$(CASE) $(CASE)_bafu

bafu-prepare:
	$(RUN) scripts/prepare_bafu_brightway.py

bafu-check:
	$(RUN) scripts/check_bafu_case_study.py bafu_case_studies/$(CASE)

bafu-clean:
	rm -rf bafu_case_studies/$(CASE)/mock_lca.zip bafu_case_studies/$(CASE)/$(CASE)_bafu.zip

# End-to-end checks in a disposable openLCA gdt-server database.
openlca-check:
	$(RUN) scripts/check_openlca.py all

openlca-foreground:
	$(RUN) scripts/check_openlca.py foreground $(if $(CASE),--case $(CASE),)

openlca-bafu:
	$(RUN) scripts/check_openlca.py bafu $(if $(CASE),--case $(CASE),)

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
		rm -rf case_studies/$$cs/.bw_project case_studies/$$cs/_extracted case_studies/$$cs/mock_lca.zip case_studies/$$cs/$$cs.zip; \
	done
