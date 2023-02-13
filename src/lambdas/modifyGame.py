import json
import boto3
from boto3.dynamodb.conditions import Attr
import uuid
from datetime import datetime
from common import checkUser, generateHashedPassword, returnErrorMessage
from parameters import getParams

dynamodb = boto3.resource('dynamodb')
gameDB = dynamodb.Table('gameDB')
playerDB = dynamodb.Table('playerDB')


def generateGame(user):
    #Check if user already in another game
    response = gameDB.scan(FilterExpression=Attr('player_names').contains(user) & Attr('status').ne("FINISHED"))
    data = response['Items']
    if len(data) != 0:
        return False, "User is already in a game", None
    
    item = {}
    item["game_id"] = str(uuid.uuid4())
    item["status"] = "WAITING"
    item["players"] = 1
    item["player_names"] = json.dumps([user])
    item["turn"] = 0
    item["action_done"] = False
    item["map"] = json.dumps([])
    item["year"] = 0
    item["map_size"] = 0

    gameDB.put_item(Item=item)
    return True, "Game generated", item["game_id"]



def deleteGame(user, game_id):
    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response: #user exists
        return False, "game_id does not exist"

    item = response["Item"]

    if "player_names" not in item:
        return False, "Error in database"

    player_names = json.loads(item["player_names"])

    if player_names[0] != user:
        return False, "User is not owner of game"

    response = gameDB.delete_item(
        Key={
            'game_id': game_id
        }
    )
    return True, "Game deleted"
        

def joinGame(user, game_id):
    response = gameDB.scan(FilterExpression=Attr('player_names').contains(user) & Attr('status').ne("FINISHED"))
    data = response['Items']
    if len(data) != 0:
        return False, "User is already in a game"

    # Check if game exists
    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response: #user exists
        return False, "game_id does not exist"

    item = response["Item"]

    # Check if game is waiting
    if "status" not in item:
        return False, "Error in database"

    status = item["status"]

    if status != "WAITING":
        return False, "Can't join an ongoing game"

    # Check if room is full
    if "players" not in item:
        return False, "Error in database"

    players = item["players"]

    if players >= 4:
        return False, "Game is already full"
    
    if "player_names" not in item:
        return False, "Error in database"

    player_names = json.loads(item["player_names"])
    player_names.append(user)

    players = players + 1

    gameDB.update_item(
        Key={'game_id': game_id},
        UpdateExpression="SET players = :players, player_names = :pn",
        ExpressionAttributeValues={":players": players, ":pn": json.dumps(player_names)},
    )
  
    return True, "Game joined"


def startGame(user, game_id):
    # Check if game exists
    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response: #user exists
        return False, "game_id does not exist"

    item = response["Item"]

    if "player_names" not in item:
        return False, "Error in database"

    player_names = json.loads(item["player_names"])

    if player_names[0] != user:
        return False, "Only game owner can start the game"

    if "status" not in item:
        return False, "Error in database"
    status = item["status"]

    if status != "WAITING":
        return False, "Game already started"


    params = getParams()
    
    status = "PLAYING"
    year = params["start_year"]
    turn = 1
    map_size = params["map_size"][int(item["players"])-1]
    game_map = []

    empty = {
                "type": None,
                "level": None,
                "owner": None
            }
    for rows in range(map_size):
        column = []
        for columns in range(map_size):
            column.append(empty)
        game_map.append(column)

    gameDB.update_item(
            Key={'game_id': game_id},
            UpdateExpression="SET #s = :s, #y = :y, #t = :t, #ms = :ms, #m = :m",
            ExpressionAttributeValues={
                ":s": status,
                ":y": year,
                ":t": turn,
                ":ms": map_size,
                ":m": json.dumps(game_map)},
            ExpressionAttributeNames={
                "#s": "status",
                "#y": "year",
                "#t": "turn",
                "#ms": "map_size",
                "#m": "map",
            }
        )

    for player in player_names:
        playerDB.update_item(
                Key={'player_id': player},
                UpdateExpression="SET #m = :m, #d = :d, #p = :p",
                ExpressionAttributeValues={
                    ":m": params["initial_money"],
                    ":d": 0,
                    ":p": 0},
                ExpressionAttributeNames={
                    "#m": "money",
                    "#d": "debt",
                    "#p": "accumulated_points",
                }
            )

    return True, "Game started"


        
def leaveGame(user, game_id):
    # Check if game exists
    response = gameDB.get_item(Key={'game_id': game_id})

    if "Item" not in response: #user exists
        return False, "game_id does not exist"

    item = response["Item"]


    if "player_names" not in item:
        return False, "Error in database"

    player_names = json.loads(item["player_names"])

    if user not in player_names:
        return False, "User is not in this game"
    player_names.remove(user)

    players = len(player_names)

    if players == 0:
        gameDB.delete_item(
            Key={
                'game_id': game_id
            }
        )
    else:
        gameDB.update_item(
            Key={'game_id': game_id},
            UpdateExpression="SET players = :players, player_names = :pn",
            ExpressionAttributeValues={":players": players, ":pn": json.dumps(player_names)},
        )

    return True, "Game left"
    


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



    success, message = checkUser(user, password)

    if not success:
        if message == "User does not exist":
            salt, key = generateHashedPassword(password)

            item = {}
            item["player_id"] = user
            item["hashed_pass"] = key.hex()
            item["salt"] = salt.hex()
            item["last_connection"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            item["money"] = 0
            item["debt"] = 0
            item["accumulated_points"] = 0

            playerDB.put_item(Item=item)
        else:
            return returnErrorMessage(message)

    game_id = None
    if params != None and "game_id" in params:
        game_id = params["game_id"]

    # If action CREATE
    # generate game and store user and hashed password
    if action == "CREATE":
        success, message, game_id = generateGame(user)

        answer = {}
        answer["message"] = message
        answer["game_id"] = game_id

    elif action == "DELETE":
        if game_id == None:
            return returnErrorMessage("game_id missing in request")

        success, message = deleteGame(user, game_id)  
        answer = {}
        answer["message"] = message
    elif action == "JOIN":
        if game_id == None:
            return returnErrorMessage("game_id missing in request")
        success, message = joinGame(user, game_id)
        answer = {}
        answer["message"] = message
    elif action == "LEAVE":
        if game_id == None:
            return returnErrorMessage("game_id missing in request")
        success, message = leaveGame(user, game_id)
        answer = {}
        answer["message"] = message
    elif action == "START":
        if game_id == None:
            return returnErrorMessage("game_id missing in request")
        success, message = startGame(user, game_id)
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

