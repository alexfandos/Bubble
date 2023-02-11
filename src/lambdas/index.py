import json
import boto3

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('gameDB')
    print("EEEEE")
    response = table.get_item(Key={'game_id': "1"})

    item = response['Item']

    item['counter'] = item['counter'] + 1

    table.put_item(Item=item)
    
    
    print(item)



    transactionResponse = {}
    transactionResponse['counter'] = str(item['counter'])


    responseObject = {}
    responseObject['statusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(transactionResponse)

    return responseObject