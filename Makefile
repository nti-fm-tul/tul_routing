build:
	python3 -m build

deploy:
	python3 -m twine upload --repository pypi dist/*