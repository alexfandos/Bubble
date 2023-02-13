import json
import boto3
from common import checkUser, returnErrorMessage
from parameters import getParams

dynamodb = boto3.resource('dynamodb')
gameDB = dynamodb.Table('gameDB')
playerDB = dynamodb.Table('playerDB')


    

def buildGameStatus(user, game_id):
    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response:
        return False, "game_id does not exist", None
    
    game = response["Item"]
    game["players"] = int(game["players"])
    game["turn"] = int(game["turn"])
    game["year"] = int(game["year"])
    game["map_size"] = int(game["map_size"])


    player_names = json.loads(game["player_names"])
    if user not in player_names:
        return False, "User is not in game", None

    player_info = []

    for player in player_names:
        response = playerDB.get_item(Key={'player_id': player})

        if "Item" not in response:
            return False, "Error in user database", None
        
        player_item = response["Item"]

        del player_item["hashed_pass"]
        del player_item["salt"]

        player_item["money"] = int(player_item["money"])
        player_item["debt"] = int(player_item["debt"])
        player_item["accumulated_points"] = int(player_item["accumulated_points"])

        player_info.append(player_item)

    status = {"game": game, "players": player_info}

    return True, "Ok", status

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

    success, message = checkUser(user, password)

    if not success:
        return returnErrorMessage(message)

    
    success, message, status = buildGameStatus(user, game_id)

    if not success:
        return returnErrorMessage(message)
    
    answer = {"message": message, "status": status}

    responseObject = {}
    responseObject['statusCode'] = 200
    responseObject['headers'] = {}
    responseObject['headers']['Content-Type'] = 'application/json'  
    responseObject['body'] = json.dumps(answer)

    return responseObject

