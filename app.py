from flask import Flask, render_template, request, g, jsonify
from pusher import Pusher
from enum import Enum
import sqlite3
import json
import time
import random

app = Flask(__name__)

app_id='351222'
key='b62d17064a726aa724fe'
secret='0b162489a33e7e38137d'

pusher = Pusher(
  app_id=app_id,
  key=key,
  secret=secret,
  cluster = "us2",
  ssl=True
)

SUITS = Enum("SUITS", "DIAMONDS SPADES CLUBS HEARTS")
STAGE = Enum("STAGE", "WAIT PREFLOP FLOP TURN RIVER SHOWDOWN")
CARDS = Enum("CARDS", "A 2 3 4 5 6 7 8 9 10 J Q K")

DATABASE = 'db/database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

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

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def show_index():
    return render_template('index.html')
    
@app.route("/login", methods=['POST'])
def login():
    req = request.get_json(force=True)
    username = req['username']
    password = req['password']
    chip = req['chip']

    # get user
    user = query("SELECT * FROM user WHERE username = ?", [username], one=True)
    if not(user):
        userId = insert("user", ["username", "password", "chip"], [username, password, chip])
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
            "chip": user["chip"]
        },
        "game": {
            "gameId": game["gameId"],
            "board": json.loads(game["board"]),
            "pot": game["pot"]
        },
        "seats": {}
    }
    for seat in seats:
        state["seats"][seat["seatNumber"]] = {
            "seatId": seat["seatId"],
            "seatNumber": seat["seatNumber"],
            "username": seat["username"],
            "chip": seat["chip"],
            "hand": json.loads(seat["hand"]),
            "status": seat["status"]
        }
    
    return jsonify(state)

# handle user siting down
@app.route("/sit", methods=['POST'])
def sit():
    req = request.get_json(force=True)
    userId = req["userId"]
    username = req["username"]
    gameId = req["gameId"]
    chip = req["chip"]
    seatNumber = req["seatNumber"]
    insert("seat", ["userId", "username", "gameId", "chip", "seatNumber", "hand"], [userId, username, gameId, chip, seatNumber, "[]"])

    seatCount = query("SELECT COUNT(*) AS COUNT FROM seat WHERE gameId = ?", [gameId], one=True)
    if seatCount["count"] > 1:
        start_game(gameId)
    
    update_state(gameId)
    return jsonify({"asdf": "asdf"})

# handle betting
@app.route("/bet", methods=['POST'])
def bet():
    req = request.get_json(force=True)
    userId = req["userId"]
    seatId = req["seatId"]
    bet = req["bet"]
    run("UPDATE seat SET status = ? WHERE seatId = ?", [bet, seatId])
    update_state(gameId)
    # check if it's time to change stage
    isChanged = check_status(gameId)
    if isChanged:
        time.sleep(2)
        update_state(gameId)

def check_status(gameId):
    seats = query("SELECT * FROM seat WHERE game.gameId = ?", [gameId])

    curentBet = None
    playerLeft = 0
    for seat in seats:
        if seat["status"] is None:
            return # haven't acted
        elif seat["status"] < 0:
            continue # folded
        elif currentBet is None:
            currentBet = seat["status"]
            playerLeft += 1
        elif currentBet != seat["status"]:
            return # bet not equal yet
        else:
            playerLeft += 1

    if playerLeft == 1:
        end_game(gameId)
    else:
        progress(gameId)
    return True

def end_game(gameId):
    # TODO: implement end game
    return

def progress(gameId):
    # TODO: implement game progression
    return

def update_state(gameId):
    game = query("SELECT * FROM game WHERE gameId = ?", [gameId], one=True)
    seats = query("SELECT * FROM seat  WHERE gameId = ?", [gameId])
    board = json.loads(game["board"])
    # update board depending on stage of the game
    if game["stage"] == STAGE.PREFLOP.name:
        board = board
    elif game["stage"] == STAGE.FLOP.name:
        board = board[:3]
    elif game["stage"] == STAGE.TURN.name:
        board = board[:4]

    state = {
        "game": {
            "gameId": game["gameId"],
            "board": board,
            "pot": game["pot"]
        },
        "seats": {}
    }
    for seat in seats:
        state["seats"][seat["seatNumber"]] = {
            "seatId": seat["seatId"],
            "seatNumber": seat["seatNumber"],
            "username": seat["username"],
            "chip": seat["chip"],
            "hand": json.loads(seat["hand"]),
            "status": seat["status"]
        }
    
    pusher.trigger("channel" + str(gameId), 'updateState', state)

# create new game
def start_game(gameId):
    seats = query("SELECT * FROM seat WHERE gameId = ?", [gameId])
    deck = []
    for card in CARDS:
        for suit in SUITS:
            deck.append({"value": card.name, "suit": suit.name})
    random.shuffle(deck)
    
    for seat in seats:
        hand = json.dumps([deck.pop(), deck.pop()])
        run("UPDATE seat SET hand = ? WHERE seatId = ?", [hand, seat["seatId"]])

    board = json.dumps(deck[-5:])
    run("UPDATE game SET board = ?, stage = ? WHERE gameId = ?", [board, STAGE.PREFLOP.name, gameId])

if __name__ == "__main__":
    app.run()