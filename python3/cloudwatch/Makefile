build:
	mkdir -p dist/python3/shipper
	mkdir -p dist/python3/custom_logger
	cp src/lambda_function.py dist
	cp ../shipper/shipper.py dist/python3/shipper
	cp ../custom_logger/custom_logger.py dist/python3/custom_logger

	(cd dist/ && zip -r logzio-cloudwatch-log-shipper.zip lambda_function.py python3/shipper/* python3/custom_logger/*)

clean:
	rm -rf dist/