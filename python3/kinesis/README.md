# Kinesis Stream Shipper - Lambda

# ⚠️ Deprecation notice ⚠️
This project is deprecated. Please refer to [this project instead](https://github.com/logzio/firehose-logs).

This is an AWS Lambda function that consumes a Kinesis stream and sends logs to Logz.io in bulk over HTTPS.

<div class="branching-container">

-   Option 1: [Manual Lambda configuration](#manual-lambda-configuration)
-   Option 2: [Automated CloudFormation deployment](#automated-cloudformation-deployment)

<!-- tab:start -->
<div id="manual-lambda-configuration">

## Manual configuration with a Lambda function

<div class="tasklist">

#### 1. Create a new Lambda function

This Lambda function will consume a Kinesis data stream and sends the logs to Logz.io in bulk over HTTP.

Open the AWS Lambda Console, and click **Create function**.
Choose **Author from scratch**, and use this information:

-   **Name**: We suggest adding the log type to the name, but you can name this function whatever you want.
-   **Runtime**: Choose **Python 3.7**
-   **Role**: Use a role that has `AWSLambdaKinesisExecutionRole` permissions.

Click **Create Function** (bottom right corner of the page). After a few moments, you'll see configuration options for your Lambda function.

You'll need this page later on, so keep it open.

#### 2. Download the Kinesis stream shipper

Download our latest Kinesis stream shipper zip file from the [releases page](https://github.com/logzio/logzio_aws_serverless/releases).

#### 3. Upload the zip file and set environment variables

In the _Function_ code section of Lambda, find the **Code entry type** list.
Choose **Upload a .ZIP file** from this list.

Click **Upload**, and choose the zip file you created earlier (`logzio-kinesis.zip`).

In the _Environment variables_ section, set your Logz.io account token, URL, and log type, and any other variables that you need to use.

###### Environment variables

| Parameter                        | Description                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TOKEN (Required)                 | The [token](https://app.logz.io/#/dashboard/settings/general) of the account you want to ship to.                                                                                                                                                                                                                                                                                           |
| REGION                           | Two-letter region code, or blank for US East (Northern Virginia). This determines your listener URL (where you're shipping the logs to) and API URL. <br> You can find your region code in the [Regions and URLs](https://docs.logz.io/user-guide/accounts/account-region.html#regions-and-urls) table.                                                                                     |
| URL (Deprecated)                 | Use REGION instead. Protocol, listener host, and port (for example, `https://<<LISTENER-HOST>>:8071`). <br > Replace `<<LISTENER-HOST>>` with your region's listener host (for example, `listener.logz.io`). For more information on finding your account's region, see [Account region](https://docs.logz.io/user-guide/accounts/account-region.html). <!-- logzio-inject:listener-url --> |
| TYPE (Default: `kinesis_lambda`) | The log type you'll use with this Lambda. This can be a [built-in log type](https://docs.logz.io/user-guide/log-shipping/built-in-log-types.html), or a custom log type. <br> You should create a new Lambda for each log type you use.                                                                                                                                                     |
| FORMAT (Default: `text`)         | `json` or `text`. If `json`, the Lambda function will attempt to parse the message field as JSON and populate the event data with the parsed fields.                                                                                                                                                                                                                                        |
| COMPRESS (Default: `true`)       | Set to `true` to compress logs before sending them. Set to `false` to send uncompressed logs.                                                                                                                                                                                                                                                                                               |
| MESSAGES_ARRAY                   | Set this ENV variable to split the a record into multiple logs based on a field containing an array of messages. For more information see [parse array of JSON objects into multiple logs](https://github.com/logzio/logzio_aws_serverless/blob/master/python3/kinesis/parse-json-array.md). **Note**: This option would work only if you set `FORMAT` to `json`.                           |

#### 4. Configure the function's basic settings

In Basic settings, we recommend starting with these settings:

-   **Memory**: 512 MB
-   **Timeout**: 1 min 0 sec

**Note**:
These default settings are just a starting point.
Check your Lambda usage regularly, and adjust these values if you need to.

#### 5. Set the Kinesis event trigger

Find the **Add triggers** list (left side of the Designer panel). Choose **Kinesis** from this list.

Below the Designer, you'll see the Configure triggers panel. Choose the **Kinesis stream** that the Lambda function will watch.

Click **Add**, and then click **Save** at the top of the page.

#### 6. Check Logz.io for your logs

Give your logs some time to get from your system to ours, and then open [Kibana](https://app.logz.io/#/dashboard/kibana).

If you still don't see your logs, see [log shipping troubleshooting](https://docs.logz.io/user-guide/log-shipping/log-shipping-troubleshooting.html).

</div>

</div>
<!-- tab:end -->

<!-- tab:start -->
<div id="automated-cloudformation-deployment">

## Automated CloudFormation deployment

**Before you begin, you'll need**:
AWS CLI,
an S3 bucket to store the CloudFormation package

<div class="tasklist">

#### 1. Download the Kinesis stream shipper

Download our latest Kinesis stream shipper zip file from the [releases page](https://github.com/logzio/logzio_aws_serverless/releases).

#### 2. Create the CloudFormation package and upload to S3

Create the CloudFormation package using the AWS CLI.
Replace `<<YOUR-S3-BUCKET>>` with the S3 bucket name where you'll be uploading this package.

```shell
curl -o sam-template.yaml https://raw.githubusercontent.com/logzio/logzio_aws_serverless/master/python3/kinesis/sam-template.yaml
aws cloudformation package \
  --template sam-template.yaml \
  --output-template-file kinesis-template.output.yaml \
  --s3-bucket <<YOUR-S3-BUCKET>>
```

#### 3. Deploy the CloudFormation package

Deploy the CloudFormation package using AWS CLI.

For a complete list of options, see the configuration parameters below the code block. 👇

```shell
aws cloudformation deploy \
--template-file $(pwd)/kinesis-template.output.yaml \
--stack-name logzio-kinesis-logs-lambda-stack \
--parameter-overrides \
  LogzioTOKEN='<<SHIPPING-TOKEN>>' \
  KinesisStream='<<KINESIS-STREAM-NAME>>' \
--capabilities "CAPABILITY_IAM"
```

###### Parameters

| Parameter                                         | Description                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LogzioTOKEN (Required)                            | Replace `<<SHIPPING-TOKEN>>` with the [token](https://app.logz.io/#/dashboard/settings/general) of the account you want to ship to. <!-- logzio-inject:account-token -->                                                                                                                                |
| KinesisStream (Required)                          | The name of the Kinesis stream where this function will listen for updates.                                                                                                                                                                                                                             |
| LogzioREGION                                      | Two-letter region code, or blank for US East (Northern Virginia). This determines your listener URL (where you're shipping the logs to) and API URL. <br> You can find your region code in the [Regions and URLs](https://docs.logz.io/user-guide/accounts/account-region.html#regions-and-urls) table. |
| LogzioURL (Deprecated)                            | Use LogzioREGION instead. Protocol, listener host, and port (for example, `https://<<LISTENER-HOST>>:8071`). <br > The [token](https://app.logz.io/#/dashboard/settings/general) of the account you want to ship to.                                                                                    |
| LogzioTYPE (Default: `kinesis_lambda`)            | The log type you'll use with this Lambda. This can be a [built-in log type](https://docs.logz.io/user-guide/log-shipping/built-in-log-types.html), or a custom log type. <br> You should create a new Lambda for each log type you use.                                                                 |
| LogzioFORMAT (Default: `text`)                    | `json` or `text`. If `json`, the Lambda function will attempt to parse the message field as JSON and populate the event data with the parsed fields.                                                                                                                                                    |
| LogzioCOMPRESS (Default: `true`)                  | Set to `true` to compress logs before sending them. Set to `false` to send uncompressed logs.                                                                                                                                                                                                           |
| KinesisStreamBatchSize (Default: `100`)           | The largest number of records to read from your stream at one time.                                                                                                                                                                                                                                     |
| KinesisStreamStartingPosition (Default: `LATEST`) | The position in the stream to start reading from. For more information, see [ShardIteratorType](https://docs.aws.amazon.com/kinesis/latest/APIReference/API_GetShardIterator.html) in the Amazon Kinesis API Reference.                                                                                 |

#### 4. Check Logz.io for your logs

Give your logs some time to get from your system to ours, and then open [Kibana](https://app.logz.io/#/dashboard/kibana).

If you still don't see your logs, see [log shipping troubleshooting](https://docs.logz.io/user-guide/log-shipping/log-shipping-troubleshooting.html).

</div>

</div>
<!-- tab:end -->

</div>
<!-- tabContainer:end -->
