.PHONY: all data clean sql model dashboard notebook test serve

all: data clean sql model dashboard notebook

data:      ## download the raw Inside Airbnb files
	python src/download_data.py
clean:     ## build data/processed/listings_clean.csv
	python src/clean.py
sql:       ## answer the business questions in SQL
	python src/run_sql.py
model:     ## train + evaluate models, export docs/model.json
	python src/train_model.py
dashboard: ## build docs/data.json for the dashboard
	python src/build_dashboard_data.py
notebook:  ## execute the analysis notebook
	jupyter nbconvert --to notebook --execute --inplace notebooks/berlin_airbnb_analysis.ipynb
test:
	pytest -q
serve:     ## open the dashboard locally on http://localhost:8000
	python -m http.server 8000 --directory docs
