NAME = pac-man.py
UV = uv
PYTHON = $(UV) run python
VENV = .venv
CONFIG_FILE ?= config.json

all: install run

install:
	$(UV) sync

run:
	$(PYTHON) $(NAME) $(CONFIG_FILE)

debug:
	$(PYTHON) -m pdb $(NAME) $(CONFIG_FILE)

lint:
	$(UV) run -m flake8 . --exclude=$(VENV),.git,__pycache__
	$(UV) run -m mypy . --exclude $(VENV) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(UV) run -m flake8 . --exclude=$(VENV),.git,__pycache__
	$(UV) run -m mypy . --exclude $(VENV) --strict

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)

re: fclean all

.PHONY: all install run debug lint lint-strict clean fclean re
