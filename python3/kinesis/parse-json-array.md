# Parse JSON array into multiple logs

One of the features of our Kinesis lambda function is to parse an array of JSON objects into discrete events to Logz.io.
That way, ElasticSearch plays nicer with these logs.

##### For Example:
For the following record:
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

Logz.io will receive the following 3 different logs:
```json
{
   "eventID": "shardId-000000000000:495451152434977345683475644582180062593244200961",
   "level": "error",
   "eventVersion": "1.0",
   "eventSource": "aws:kinesis",
   "type": "kinesis_lambda",
   "timestamp":"time",
   "message":"something went wrong in service A"
}
```
```json
{
   "eventID": "shardId-000000000000:495451152434977345683475644582180062593244200961",
   "level": "error",
   "eventVersion": "1.0",
   "eventSource": "aws:kinesis",
   "type": "kinesis_lambda",
   "timestamp":"time",
   "message":"something went wrong also in service B"
}
```
```json
{
   "eventID": "shardId-000000000000:495451152434977345683475644582180062593244200961",
   "level": "info",
   "eventVersion": "1.0",
   "eventSource": "aws:kinesis",
   "type": "kinesis_lambda",
   "timestamp":"time",
   "message":"something totally normal happened in service C"
}
```

Notice all the metadata is the same for all the logs except for the `info` field which the inner logs override.

### How to enable multiple logs parsing

All you need to do to enable this feature is to set the environment variable `MESSAGES_ARRAY` to point to the field containing the JSON array.
For the example above, we will set the ENV variable `MESSAGES_ARRAY` value to `messages`.

**Note**: This option would work only if you set `FORMAT` to `json`.