build:
	mkdir -p dist/python3/shipper
	cp -r ../shipper/shipper.py dist/python3/shipper
	cp src/lambda_function.py dist
	cd dist && zip logzio-cloudwatch lambda_function.py python3/shipper/*

clean:
	rm -rf dist/
