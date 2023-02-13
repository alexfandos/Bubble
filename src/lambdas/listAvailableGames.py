import json
import boto3
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('gameDB')
    print("EEEEE")
    response = table.scan(FilterExpression=Attr('status').eq('WAITING') & Attr('players').lt(7))

    data = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])


    transactionResponse = {}
    transactionResponse['data'] = str(data)


    responseObject = {}
    responseObject['statusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(transactionResponse)

    return responseObject