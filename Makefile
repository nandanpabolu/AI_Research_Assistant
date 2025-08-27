.PHONY: help install run test clean lint format deploy

help:  ## Show this help message
	@echo "AI Research Assistant - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:  ## Run the application locally
	. venv/bin/activate && streamlit run app.py

run-prod:  ## Run the application in production mode
	. venv/bin/activate && streamlit run app.py --server.port 8501 --server.address 0.0.0.0

test:  ## Run tests
	. venv/bin/activate && python -m pytest tests/ -v

lint:  ## Run linting checks
	. venv/bin/activate && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	. venv/bin/activate && flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format:  ## Format code with black
	. venv/bin/activate && black . --line-length 127

clean:  ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".coverage" -delete
	rm -rf build/ dist/ .eggs/

deploy:  ## Deploy to Streamlit Cloud (requires git push first)
	@echo "To deploy to Streamlit Cloud:"
	@echo "1. git add . && git commit -m 'Update for deployment'"
	@echo "2. git push origin main"
	@echo "3. Go to https://share.streamlit.io/ and connect your repo"

docker-build:  ## Build Docker image
	docker build -t ai-research-assistant .

docker-run:  ## Run Docker container
	docker run -p 8501:8501 ai-research-assistant

requirements:  ## Update requirements.txt
	. venv/bin/activate && pip freeze > requirements.txt

setup-dev:  ## Setup development environment
	. venv/bin/activate && pip install -e ".[dev]"

docs:  ## Build documentation
	. venv/bin/activate && cd docs && make html

check:  ## Run all checks (lint, test, format)
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) format



