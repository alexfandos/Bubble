import json
import boto3
from boto3.dynamodb.conditions import Attr
import os
import hashlib
import uuid
from datetime import datetime


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



def generateGame(user, password):

    success, message = checkUser(user, password)

    dynamodb = boto3.resource('dynamodb')
    
    gameDB = dynamodb.Table('gameDB')

    if success:
        #Check if user already in another game

        
        response = gameDB.scan(FilterExpression=(Attr('player1').eq(user) | Attr('player2').eq(user) | Attr('player3').eq(user) | Attr('player4').eq(user)) & Attr('status').ne("FINISHED"))
        data = response['Items']
        if len(data) != 0:
            return False, "User is already in a game", None
    
    else:
        if message == "User does not exist":
            playerDB = dynamodb.Table('playerDB')

            salt, key = generateHashedPassword(password)

            item = {}
            item["player_id"] = user
            item["hashed_pass"] = key.hex()
            item["salt"] = salt.hex()
            item["last_connection"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            playerDB.put_item(Item=item)
        else:
            return success, message, None

    item = {}
    item["game_id"] = str(uuid.uuid4())
    item["status"] = "WAITING"
    item["players"] = 1
    item["player1"] = user
    item["player2"] = ""
    item["player3"] = ""
    item["player4"] = ""
    item["player_info"] = "/{/}"
    item["turn"] = 0
    item["action_done"] = False
    item["map"] = "/{/}"

    gameDB.put_item(Item=item)
    return True, "Game generated", item["game_id"]



def deleteGame(user, password, game_id):
    success, message = checkUser(user, password)
    dynamodb = boto3.resource('dynamodb')
    if success:
        gameDB = dynamodb.Table('gameDB')
        response = gameDB.get_item(Key={'game_id': game_id})

        if "Item" not in response: #user exists
            return False, "game_id does not exist"

        item = response["Item"]

        if "player1" not in item:
            return False, "Error in database"

        player1 = item["player1"]

        if player1 != user:
            return False, "User is not owner of game"

        response = gameDB.delete_item(
            Key={
                'game_id': game_id
            }
        )
        return True, "Game deleted"
    else:
        return success, message


def returnErrorMessage(message):
    responseObject = {}
    responseObject['statusCode'] = 500
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(message)
    return responseObject



def lambda_handler(event, context):
    
    if "queryStringParameters" in event:
        params = event["queryStringParameters"]
    else:
        return returnErrorMessage("No params")

    if params != None and "action" in params:
        action = params["action"]
    else:
        return returnErrorMessage("Action is missing in request")

    if params != None and "user" in params:
        user = params["user"]
        if user == "":
            return returnErrorMessage("User can't be empty")
    else:
        return returnErrorMessage("User is missing in request")

    if params != None and "password" in params:
        password = params["password"]
        if password == "":
            return returnErrorMessage("Password can't be empty")
    else:
        return returnErrorMessage("Password is missing in request")

    # If action CREATE
    # generate game and store user and hashed password
    if action == "CREATE":
        success, message, game_id = generateGame(user, password)

        answer = {}
        answer["message"] = message
        answer["game_id"] = game_id

    elif action == "DELETE":
        if params != None and "game_id" in params:
            game_id = params["game_id"]
            success, message = deleteGame(user, password, game_id)
        else:
            return returnErrorMessage("game_id missing in request")
        answer = {}
        answer["message"] = message
    else:
        return returnErrorMessage("Unkown action")


    responseObject = {}
    responseObject['statusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(answer)

    return responseObject

