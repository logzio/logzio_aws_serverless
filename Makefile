build:
	mkdir -p dist/
	zip -j dist/logzio-cloudwatch-log-shipper.zip src/lambda_function.py src/shipper.py

clean:
	rm -rf dist/