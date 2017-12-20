# CloudWatch Logs Shipper - Lambda

This is AWS Lambda function to collect Cloudwatch logs using lambda and send them to Logz.io in a bulk over HTTP.

### Creating Lambda Function

  - Sign in to your AWS account and open the AWS Lambda console. 
  - Click Create function, to create a new Lambda function.
  - Select the Author from scratch, and enter the following information:
    - Name -  enter a name for your new Lambda function. We suggest to add log type to your name. 
    - Runtime - from the drop-down menu, select Python 2.7 as the function’s runtime.
    - Role - leave the default Choose an existing role and under Existing role, select lambda_basic_execution
    - Hit the Create Function button in the bottom right corner of the page.
 
### Uploading and configuring the Logz.io Lambda shipper
 - In the Function Code section open the Code entry type menu, and select Edit code inline. 
 - Copy the Lambda function into the editor. 
 - In Environment variables section to set your Logz.io token, URL and log type:
    - TOKEN: Go to your logz.io app and press the account button in the top right corner, you can find your token in account settings.
    - TYPE: Enter your log type you are going to use with this Lambda, notice that you should set a new Lambda for each log type you are using. Go here, to find all the log types we support.
    - URL: If you are in the EU region insert https://listener-eu.logz.io:8071 otherwise use https://listener.logz.io:8071. You can tell which region you are in by checking the login url, if your environment says app.logz.io then your in the US, if it says app-eu.logz.io then you are in the EU.
 - In Basic Settings section - We recommend to start by setting memory to 512(MB) and a 1(MIN) timeout, and then subsequently adjusting these values based on trial and error and according to your Lambda usage.

### Setting CloudWatch log event trigger
 - Under Add triggers at the top of the page, select the CloudWatch Log trigger.
 - In the Configure triggers section, you will then be required to enter the log group from which the Logz.io Lambda collects the logs. You will also need to enter a filter name. 
 - Click Add to add the trigger and Save at the top of the page to save all your configurations. 
