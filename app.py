from flask import Flask, render_template, request, g, jsonify  # tools in flask library
from pusher import Pusher  # push messages to the client side (Pusher library)
from enum import Enum 
import itertools
import sqlite3
import json  # javascript object
import time
import random

app = Flask(__name__)  # creates a new variable called "app", and its a new flask object

app_id = '351222'
key = 'b62d17064a726aa724fe'
secret = '0b162489a33e7e38137d'  # sign up pusher, our account keys

pusher = Pusher(
  app_id=app_id,
  key=key,
  secret=secret,
  cluster="us2",
  ssl=True
)

STAGE = Enum("STAGE", "WAIT PREFLOP FLOP TURN RIVER SHOWDOWN")  # creates a variable with multiple types (google it)

DATABASE = 'db/database.db'  # location of the database


def get_db():
    """ grab connection to the database"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    """ initialize the database"""
    with app.app_context():
        db = get_db()  # gets the database connection
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())  # execute sql code that is in schema.sql
        db.commit()


def query(query, args=(), one=False):
    """ retrieving info from database"""
    cur = get_db().execute(query, args)
    result = cur.fetchall()  # result is the answer to the query
    cur.close()
    return (result[0] if result else None) if one else result


def insert(table, fields=(), values=()):
    conn = get_db()
    cur = conn.cursor()
    query = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table,
        ', '.join(fields),
        ', '.join(['?'] * len(values))
    )
    cur.execute(query, values)
    conn.commit()
    id = cur.lastrowid
    cur.close()
    return id


def run(query, args=()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    cur.close()


@app.teardown_appcontext  # decorate this function
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route("/")
def show_index():
    return render_template('index.html')  # return this html to the client, so client can display it


@app.route("/login", methods=['POST'])
def login():
    req = request.get_json(force=True)
    username = req['username']
    password = req['password']
    stackSize = req['stackSize']

    # get user
    user = query("SELECT * FROM user WHERE username = ?", [username], one=True)
    if not(user):
        userId = insert("user", ["username", "password", "stackSize"], [username, password, stackSize])
        user = query("SELECT * FROM user WHERE userId = ?", [userId], one=True)
    
    # get new game
    game = query("SELECT * FROM game", one=True)
    if not(game):
        gameId = insert("game", ["gameName", "board", "stage"], ["gameTest", "[]", STAGE.WAIT.name])
        game = query("SELECT * FROM game WHERE gameId = ?", [gameId], one=True)
    
    # get all the current seats
    seats = query("SELECT * FROM seat WHERE gameId = ?", [game["gameId"]])
    state = {
        "user": {
            "userId": user["userId"],
            "username": user["username"],
            "stackSize": user["stackSize"]
        }
    }
    construct_state(state, game, seats)
    return jsonify(state)


# handle user siting down
@app.route("/sit", methods=['POST'])
def sit():
    req = request.get_json(force=True)  # this is flask API function, returns whatever the client sends
    userId = req["userId"]
    username = req["username"]
    gameId = req["gameId"]
    stackSize = req["stackSize"]
    seatNumber = req["seatNumber"]
    insert("seat", ["userId", "username", "gameId", "stackSize", "seatNumber", "hand"], [userId, username, gameId, stackSize, seatNumber, "[]"])

    seatCount = query("SELECT COUNT(*) AS COUNT FROM seat WHERE gameId = ?", [gameId], one=True)
    if seatCount["count"] > 1:
        start_game(gameId)
    
    push_state(gameId)
    return jsonify({"success": "true"})


# handle betting
@app.route("/bet", methods=['POST'])
def bet():
    req = request.get_json(force=True)  # json format = strings
    userId = req["userId"]
    seatId = req["seatId"]
    betSize = int(req["betSize"])
    seat = query("SELECT * FROM seat WHERE seatId = ?", [seatId], one=True)
    stackSize = seat["stackSize"]
    if betSize > 0:
        stackSize -= betSize
        if seat["betSize"] is not None: # None is a python keyword
            stackSize += seat["betSize"]
    run("UPDATE seat SET betSize = ?, stackSize = ? WHERE seatId = ?", [betSize, stackSize, seatId]) # update the seat's betsize and stacksize
    push_state(seat["gameId"])
    # check if it's time to change stage
    check_betSize(seat["gameId"])
    return jsonify({"success": "true"})


def check_betSize(gameId):
    seats = query("SELECT * FROM seat WHERE gameId = ?", [gameId])

    currentBet, playerLeft = None, 0
    for seat in seats:
        if seat["betSize"] is None:
            return # haven't acted
        elif seat["betSize"] < 0:
            continue # folded
        elif currentBet is None:
            currentBet = seat["betSize"]
            playerLeft += 1
        elif currentBet != seat["betSize"]:
            return # bet not equal yet
        else:
            playerLeft += 1

    progress(gameId)


# decides who win and assign the pot(s)
def end_game(gameId):

    game = query("SELECT * FROM game WHERE gameId = ?", [gameId], one=True)
    seats = query("SELECT * FROM seat WHERE gameId = ?", [gameId])
    board = json.loads(game["board"])
    bestValue = None  # current highest valued hand
    bestSeats = []
    for seat in seats:
        hand = json.loads(seat["hand"])
        bestCombo = max(itertools.combinations(board + hand, 5), key=hand_rank)
        handValue = hand_rank(bestCombo)
        if len(bestSeats) == 0 or handValue > bestValue:
            bestValue = handValue
            bestSeats = [seat]  # create a new array (bestSeats) with a single element "seat"
        elif handValue == bestValue:
            bestSeats.append(seat)

    for seat in bestSeats:
        stackSize = seat["stackSize"] + (game["pot"] // len(bestSeats))
        run("UPDATE seat SET stackSize = ? WHERE seatId = ?", [stackSize, seat["seatId"]])

    run("UPDATE game SET board = ?, pot = ?, stage = ? WHERE gameId = ?", ["[]", 0, STAGE.WAIT.name, gameId])
    time.sleep(1)
    push_state(gameId)
    time.sleep(1)
    start_game(gameId)
    push_state(gameId)


def hand_rank(hand):
    rankings = {(4, 1): 7, (3, 2): 6, (3, 1, 1): 3, (2, 2, 1): 2, (2, 1, 1, 1): 1, (1, 1, 1, 1, 1): 0}
    counts, ranks = groups(['--23456789TJQKA'.index(r) for r,s in hand])
    if ranks == (14, 5, 4, 3, 2):
        ranks = (5, 4, 3, 2, 1)
    straight = len(ranks) == 5 and max(ranks) - min(ranks) == 4
    flush = len(set([s for r,s in hand])) == 1
    return max(rankings[counts], 4 * straight + 5 * flush), ranks


def groups(items):
    groups = sorted([(items.count(x), x) for x in set(items)], reverse=True) # [(3, 14), (2, 13)]
    return zip(*groups) # => [(3, 2), (14, 13)]


def progress(gameId):
    game = query("SELECT * FROM game WHERE gameId = ?", [gameId], one=True)
    seats = query("SELECT * FROM seat  WHERE gameId = ?", [gameId])

    newStage = ""
    pot = game["pot"]
    if game["stage"] == STAGE.PREFLOP.name:
        newStage = STAGE.FLOP.name
    elif game["stage"] == STAGE.FLOP.name:
        newStage = STAGE.TURN.name
    elif game["stage"] == STAGE.TURN.name:
        newStage = STAGE.RIVER.name
    elif game["stage"] == STAGE.RIVER.name:
        newStage = STAGE.SHOWDOWN.name

    for seat in seats:
        if seat["betSize"] > 0:
            pot += seat["betSize"]
        run("UPDATE seat SET betSize = ? WHERE seatId = ?", [None, seat["seatId"]])

    run("UPDATE game SET stage = ?, pot = ? WHERE gameId = ?", [newStage, pot, gameId])
    time.sleep(1)
    push_state(gameId)
    if newStage == STAGE.SHOWDOWN.name:
        end_game(gameId)


def push_state(gameId):
    game = query("SELECT * FROM game WHERE gameId = ?", [gameId], one=True)
    seats = query("SELECT * FROM seat  WHERE gameId = ?", [gameId])
    state = {}
    construct_state(state, game, seats)
    pusher.trigger("channel" + str(gameId), 'updateState', state)


def construct_state(state, game, seats):
    board = json.loads(game["board"])
    # update board depending on stage of the game
    if game["stage"] == STAGE.PREFLOP.name:
        board = []
    elif game["stage"] == STAGE.FLOP.name:
        board = board[:3]
    elif game["stage"] == STAGE.TURN.name:
        board = board[:4]
        
    state["game"] = {
        "gameId": game["gameId"],
        "board": board,
        "pot": game["pot"]
    }
    state["seats"] = {}
    for seat in seats:
        state["seats"][seat["seatNumber"]] = {
            "seatId": seat["seatId"],
            "seatNumber": seat["seatNumber"],
            "username": seat["username"],
            "userId": seat["userId"],
            "stackSize": seat["stackSize"],
            "hand": json.loads(seat["hand"]),
            "betSize": seat["betSize"]
        }


# create new game
def start_game(gameId):
    seats = query("SELECT * FROM seat WHERE gameId = ?", [gameId])
    deck = [r+s for r in '23456789TJKA' for s in 'shdc']
    random.shuffle(deck)
    
    for seat in seats:
        hand = json.dumps([deck.pop(), deck.pop()])
        run("UPDATE seat SET hand = ? WHERE seatId = ?", [hand, seat["seatId"]])

    board = json.dumps(deck[:5])
    run("UPDATE game SET board = ?, stage = ? WHERE gameId = ?", [board, STAGE.PREFLOP.name, gameId])

if __name__ == "__main__":
    app.run()