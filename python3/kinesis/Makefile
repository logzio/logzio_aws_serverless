build:
	mkdir -p dist/python3/shipper
	cp src/lambda_function.py dist
	cp ../shipper/shipper.py dist/python3/shipper

	(cd dist/ && zip -r logzio-kinesis-log-shipper.zip lambda_function.py python3/shipper/*)

clean:
	rm -rf dist/