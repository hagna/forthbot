COVERAGE = `which coverage`
COVERAGE_PROCESS_START = $(PWD)/.coveragerc
export COVERAGE_PROCESS_START
TRIAL = `which trial`
TEST_MODULE = smd

help:
	cat Makefile

clean:
	-find . -name "*.pyc" -exec rm {} \;
	-rm -rf _trial_temp
	-rm *.tgz
	-rm -rf MANIFEST
	-rm -rf htmlcov
	-rm -r doc/html/*.html
	-rm -r doc/html/api/*.html
	-rm .coverage.*
	-rm .coverage

tar:
	make clean
	python setup.py sdist

# converts the .rst files in doc/rst to HTML files in doc/html
htmldoc:
	-rm doc/html/*.html
	cd doc && python makehtml.py

version:
	@python -c "import smd; print smd.__version__"

bump:
	@./bumpversion.py

covrun:
	-$(COVERAGE) run $(TRIAL) $(TEST_MODULE)
	-mv _trial_temp/.coverage.* .
	$(COVERAGE) combine

covreport:
	$(COVERAGE) report

covhtml:
	$(COVERAGE) html

# makes the API Documentation in doc/html/api
pydoctor:
	bash mkpydoctor.sh

