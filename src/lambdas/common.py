import boto3
import hashlib
import os
from datetime import datetime
import json


def checkAndExtractFromRequest(fields, request):
    if isinstance(fields, str):
        if fields not in request:
            return False, fields + " is missing in request"
        return True, request[fields]
    else:
        results = []
        for field in fields:
            if field not in request:
                return False, field + " is missing in request"
            results.append(request[field])
    return True, results


def generateHashedPassword(password, salt = None):
    if salt == None:
        salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256', # The hash digest algorithm for HMAC
        password.encode('utf-8'), # Convert the password to bytes
        salt, # Provide the salt
        100000 # It is recommended to use at least 100,000 iterations of SHA-256 
    )
    return salt, key


def checkUser(user, password):
    dynamodb = boto3.resource('dynamodb')
    playerDB = dynamodb.Table('playerDB')

    response = playerDB.get_item(Key={'player_id': user})

    if "Item" in response: #user exists
        item = response['Item']
        if "salt" not in item:
            return False, "Error in database"
        salt = bytes.fromhex(item['salt'])
        if "hashed_pass" not in item:
            return False, "Error in database"
        user_hashed_pass = item['hashed_pass']

        _, key = generateHashedPassword(password, salt)

        print("User hash: " + user_hashed_pass)
        print("New hash: " + key.hex())

        if user_hashed_pass != key.hex():
            print("Password is incorrect.")
            return False, "Password is incorrect."
        
        #Update last connection

        playerDB.update_item(
            Key={'player_id': user},
            UpdateExpression="SET last_connection = :new_value",
            ExpressionAttributeValues={":new_value": datetime.now().strftime("%d/%m/%Y %H:%M:%S")},
        )
        return True, "Ok"
    else:
        return False, "User does not exist"

def returnErrorMessage(message):
    responseObject = {}
    responseObject['statusCode'] = 500
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(message)
    return responseObject