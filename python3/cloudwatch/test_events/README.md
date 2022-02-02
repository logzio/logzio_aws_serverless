# Working with test events

You can generate test events using the Logz.io Lambda test events generator and add these events to your Lambda function. This functionality is currently only available on Linux & macOS.


## Generate a test event

1. In your terminal, run the following command:
  
   ```shell
   bash <(curl -s https://raw.githubusercontent.com/logzio/logzio_aws_serverless/tree/master/python3/cloudwatch/test_events/test_event_generator.sh)      
   ```
               
   This script generates a test event with a UTC timestamp of the moment you run the script.
               
2. Copy the output JSON.

## Add the generated test event to your Lambda function

1. Select the Lambda function that you need to add the test event to.
2. Open the **Test** tab.
3. Select **New event**.
4. In the **Template** field, select **CloudWatch Logs**.
5. In the **Name** field, enter a name for the test event. No specific naming convention is required. 
6. Populate the body field with the output JSON of the test event generated in the previous step.
7. Select **Format** to format the test event.
8. Select **Save changes**.

## Run the test event

To run the test event, select **Test** in the **Test** tab. The Lambda function will run and generate two logs in your account.
