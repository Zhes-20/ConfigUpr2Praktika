PYTHON ?= python3

.PHONY: run test demo

run:
	$(PYTHON) -m src.app $(ARGS)

test:
	$(PYTHON) -m unittest discover -s tests -v

demo:
	bash examples/stage1_demo.sh
	bash examples/stage2_demo.sh
