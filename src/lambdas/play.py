import json
import boto3
from common import checkUser, returnErrorMessage, checkAndExtractFromRequest
from parameters import getParams

dynamodb = boto3.resource('dynamodb')
gameDB = dynamodb.Table('gameDB')
playerDB = dynamodb.Table('playerDB')


def passTurn(game, player_info):
    pass

def destroy(game, player_info, coordinates):
    pass

def upgrade(game, player_info, coordinates, level):
    pass

def build(game, player_info, coordinates, type, level):
    pass

def askLoan(game, player_info, amount):
    pass

def payLoan(game, player_info, amount):
    pass

def play(game, player_info, action, params):

    if action == "PASS":
        return passTurn(game, player_info)

    elif action == "ASK_LOAD":
        success, result = checkAndExtractFromRequest("amount", params)
        if not success:
            return False, result
        return askLoan(game, player_info, result)

    elif action == "PAY_LOAN":
        success, message = checkAndExtractFromRequest("amount", params)
        if not success:
            return False, result
        return payLoan(game, player_info, result)

    elif action == "DESTROY":
        success, message = checkAndExtractFromRequest("coordinates", params)
        if not success:
            return False, result
        return destroy(game, player_info, result)
    
    elif action == "UPGRADE":
        success, message = checkAndExtractFromRequest(["coordinates", "level"], params)
        if not success:
            return False, result
        return destroy(game, player_info, result[0], result[1])
    
    elif action == "BUILD":
        success, message = checkAndExtractFromRequest(["coordinates", "type", "level"], params)
        if not success:
            return False, result
        return destroy(game, player_info, result[0], result[1], result[2])
    else:
        return False, "Amount is missing in request"

            

def lambda_handler(event, context):
    
    if "queryStringParameters" in event:
        params = event["queryStringParameters"]
    else:
        return returnErrorMessage("No params")

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

    if params != None and "game_id" in params:
        game_id = params["game_id"]
    else:
        return returnErrorMessage("Game_id is missing in request")

    if params != None and "action" in params:
        action = params["action"]
    else:
        return returnErrorMessage("Action is missing in request")

    success, message = checkUser(user, password)

    if not success:
        return returnErrorMessage(message)

    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response:
        return returnErrorMessage("game_id does not exist")

    game = response["Item"]
    if user not in json.loads(game["player_names"]):
        return returnErrorMessage("User is not in game")

    response = playerDB.get_item(Key={'player_id': user})
    if "Item" not in response:
        return returnErrorMessage("player_id does not exist")
    
    player_info = response["Item"]
    
    success, message = play(game, player_info, action, params)

    if not success:
        return returnErrorMessage(message)
    
    answer = {"message": message, "status": status}

    responseObject = {}
    responseObject['statusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(answer)

    return responseObject

