# CloudWatch Logs Shipper - Lambda

This is an AWS Lambda function that collects CloudWatch logs and sends them to Logz.io in bulk over HTTP.
For detailed information, read our [blog post](https://logz.io/blog/cloudwatch-lambda-shipper/).

## Step 1: Deploy the Lambda function

You have two options to deploy:

* [Option 1: Manually deploy the Lambda function](#Option-1-Manually-deploy-the-Lambda-function)

* [Option 2: Automatic deployment using CloudFormation](#Option-2-Automatic-deployment-using-CloudFormation)


### Option 1: Manually deploy the Lambda function

#### Create the Lambda Function

1. Sign in to your AWS account and open AWS Lambda.
2. Click **Create function** to create a new Lambda function.
3. Choose **Author from scratch**, and enter the following information:
    - **Name:** Short name for your new Lambda function. We suggest adding the log type to the name.
    - **Runtime:** Choose **Python 2.7**
    - **Role:** Click **Create new role from template(s)**. Under **Existing role**, select **Basic Edge Lambda permissions**
4. Click **Create Function**, in the bottom right corner of the page. You'll need this in the next step, so keep this page open.

#### Upload and configure the Logz.io Lambda shipper

1. Clone the logzio_aws_serverless repo to your machine (https://github.com/logzio/logzio_aws_serverless.git).
2. `cd` into `logzio_aws_serverless/cloudwatch/`. Zip 'lambda_function.py' and 'shipper.py' with one of these options:
    - `make build` creates the zip at 'dist/logzio-cloudwatch-log-shipper.zip'
    - `mkdir dist; cp -r ../shipper dist/ && cp src/lambda_function.py dist/ && cd dist/ && zip logzio-cloudwatch shipper/* lambda_function.py`
3. In the **Function code** section of Lambda, choose **Upload a .ZIP file** from the **Code entry type list**.
4. Click **Upload**, and choose the zip you created on your machine.
5. In the **Environment variables** section, set your Logz.io account token, URL, and log type:

    | Key | Value | Default |
    |---|---|---|
    | `TOKEN` | **Required**. Your Logz.io account token, which can find in your [Settings page](https://app.logz.io/#/dashboard/settings/general) in Logz.io. | |
    | `TYPE` | **Required**. The log type you'll use with this Lambda. Please note that you should create a new Lambda for each log type you use. This can be a [built-in log type](https://docs.logz.io/user-guide/log-shipping/built-in-log-types.html), or your custom log type | |
    | `FORMAT` | `json` or `text`. If `json`, the lambda function will attempt to parse the message field as JSON and populate the event data with the parsed fields. | `text` |
    | `URL` | **Required**. Your Logz.io listener URL. If you are in the EU region, use `https://listener-eu.logz.io:8071`. Otherwise, use `https://listener.logz.io:8071`. If you don't know your region, check your login URL. _app-eu.logz.io_ is the EU data center. _app.logz.io_ is the US data center. |
    | `COMPRESS` | If `true`, the Lambda will send compressed logs. If `false`, the Lambda will send uncompressed logs. | `false` |
    | `ENRICH` | Enriche CloudWatch events with custom properties at shipping time. The format is `key1=value1;key2=value2`. By default is empty. | |

6. In **Basic settings**, we recommend setting **Memory** to 512 MB, and setting **Timeout** to 1 min 0 sec. Keep an eye on your Lambda usage, and adjust these values accordingly.
7. Leave the other settings as default.

### Option 2: Automatic deployment using CloudFormation

**Prerequisites:** AWS CLI and an S3 bucket

1. Clone the logzio_aws_serverless repo to your machine (https://github.com/logzio/logzio_aws_serverless.git).
2. `cd` into `logzio_aws_serverless/cloudwatch/`. Zip 'lambda_function.py' and 'shipper.py' with one of these options:
    - `make build` creates the zip at 'dist/logzio-cloudwatch-log-shipper.zip'
    - `mkdir dist; cp -r ../shipper dist/ && cp src/lambda_function.py dist/ && cd dist/ && zip logzio-cloudwatch shipper/* lambda_function.py`
3. Upload the package to your S3 bucket.
 
     ```bash
     aws cloudformation package 
        --template sam-template.yaml
        --output-template-file cloudformation-template.output.yaml 
        --s3-bucket <your_s3_bucket>
     ```
 
4. The following is an example on how to deploy CloudFormation. Replace the parameters with the ones you need:

    ```bash
    aws cloudformation deploy 
    --template-file $(pwd)/cloudformation-template.output.yaml 
    --stack-name logzio-cloudwatch-logs-lambda-stack 
    --parameter-overrides  
       LogzioTOKEN='<your_logzio_token>'  
    --capabilities "CAPABILITY_IAM"
    ```
 
    | Key | Value | Default |
    |---|---|---|
    | `LogzioTOKEN` | **Required**. Your Logz.io account token, which can find in your [Settings page](https://app.logz.io/#/dashboard/settings/general) in Logz.io. | |
    | `LogzioTYPE` | The log type you'll use with this Lambda. Please note that you should create a new Lambda for each log type you use. This can be a [built-in log type](https://docs.logz.io/user-guide/log-shipping/built-in-log-types.html), or your custom log type | `logzio_cloudwatch_logs` |
    | `LogzioFORMAT` | `json` or `text`. If `json`, the lambda function will attempt to parse the message field as JSON and populate the event data with the parsed fields. | `text` |
    | `LogzioURL` | Your Logz.io listener URL. If you are in the EU region, use `https://listener-eu.logz.io:8071`. Otherwise, use `https://listener.logz.io:8071`. If you don't know your region, check your login URL. _app-eu.logz.io_ is the EU data center. _app.logz.io_ is the US data center. | `https://listener.logz.io:8071` |
    | `LogzioCOMPRESS` | If `true`, the Lambda will send compressed logs. If `false`, the Lambda will send uncompressed logs. | `false` |

## Step 2: Set up CloudWatch log event trigger

1. In the **Designer** section (at the top of the page), find the **Add triggers** list. Choose **CloudWatch Logs** from this list.
2. In the **Configure triggers** section, choose the **Log group** from which the Logz.io Lambda collects the logs.
3. Type a **Filter name**.
4. Click **Add** to add the trigger, and then click **Save** at the top of the page to save all your configurations.

