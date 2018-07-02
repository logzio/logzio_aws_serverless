# CloudWatch Logs Shipper - Lambda

This is an AWS Lambda function that collects CloudWatch logs and sends them to Logz.io in bulk, over HTTP.
For detailed information you can check this blog [post](https://logz.io/blog/cloudwatch-lambda-shipper/)

## Step 1 - Creating the Lambda Function

1. Sign in to your AWS account and open the AWS Lambda console.
2. Click **Create function**, to create a new Lambda function.
3. Select Author from scratch, and enter the following information:
  - Name -  enter a name for your new Lambda function. We suggest adding the log type to the name.
  - Runtime - from the drop-down menu, select Python 2.7 as the function’s runtime.
  - Role - press on *Create new role from template(s)* , and under Existing role, select *Basic Edge Lambda permissions*
4. Hit the **Create Function** button in the bottom-right corner of the page.

## Step 2 - Uploading and configuring the Logz.io Lambda shipper
1. Zip 'lambda_function.py' and 'shipper.py' with one of the following two options:
  - `make build` will create the zip at 'dist/logzio-cloudwatch-log-shipper.zip'
  - `zip logzio-cloudwatch-log-shipper lambda_function.py shipper.py`
2. In the Function Code section, open the Code entry type menu, and select *Upload a .ZIP file*.
3. Select the zip you created at 1.
4. In the Environment variables section, set your Logz.io token, URL and log type:
  - TOKEN: your Logz.io account token. Can be retrieved on the Settings page in the Logz.io UI.
  - TYPE: the log type you are going to use with this Lambda. Please note that you should create a new Lambda for each log type you are using. For a list of the log types we support, go [here]. 
  - FORMAT: 'JSON' is supported, if the 'FORMAT' JSON is set the lambda function will attempt to parse the message field as json and populate the event data with the parsed fields.
  - URL: the Logz.io listener URL. If you are in the EU region insert https://listener-eu.logz.io:8071. Otherwise, use https://listener.logz.io:8071. You can tell which region you are in by checking your login URL - *app.logz.io* means you are in the US. *app-eu.logz.io* means you are in the EU.
5. In the Basic Settings section, we recommend to start by setting memory to 512(MB) and a 1(MIN) timeout, and then subsequently adjusting these values based on trial and error, and according to your Lambda usage.
6. Leave the other settings as default

## Step 3 - Setting CloudWatch log event trigger
1. Under Add triggers at the top of the page, select the CloudWatch Log trigger.
2. In the Configure triggers section, you will then be required to enter the log group from which the Logz.io Lambda collects the logs. You will also need to enter a filter name.
3. Click **Add** to add the trigger and **Save** at the top of the page to save all your configurations.

[here]: https://support.logz.io/hc/en-us/articles/210205985-Which-log-types-are-preconfigured-on-the-Logz-io-platform-
