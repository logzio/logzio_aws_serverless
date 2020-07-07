# Parse JSON array into multiple logs

One of the features of our Kinesis lambda function is to parse an array of JSON objects into discrete events to Logz.io.

##### For Example:
For the following event:
```json
{
   "eventID": "shardId-000000000000:495451152434977345683475644582180062593244200961",
   "level": "warning",
   "eventVersion": "1.0",
   "eventSource": "aws:kinesis",
   "type": "kinesis_lambda",
   "timestamp":"time",
   "messages":[
      {
         "message":"something went wrong in service A",
         "level":"error"
      },
      {
         "message":"something went wrong also in service B",
         "level":"error"
      },
      {
         "message":"something totally normal happened in service C",
         "level":"info"
      }
   ]
}
```


There are a few benefits for this feature:
   