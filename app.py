from flask import Flask, render_template, request, g, jsonify
from pusher import Pusher
import sqlite3
import json
from enum import Enum

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
    else:
        userId = user["userId"]
    
    # get new game
    game = query("SELECT * FROM game", one=True)
    if not(game):
        gameId = insert("game", ["gameName", "stage"], ["gameTest", STAGE.WAIT.value])
    else:
        gameId = game["gameId"]
    
    return jsonify({"userId": userId, "username": username, "chip": chip, "game": gameId})

# handle user siting down
@app.route("/sit", methods=['POST'])
def sit():
    req = request.get_json(force=True)
    userId = req["userId"]
    gameId = req["gameId"]
    chip = req["chip"]
    seatNumber = req["seatNumber"]
    insert("seat", ["userId", "gameId", "chip", "seatNumber"], [userId, gameId, chip, seatNumber])

    game = query("SELECT * FROM game WHERE gameId = ?", one=True)
    if game['stage'] == "WAIT":
        start_game(game["gameId"])

# handle 
@app.route("/bet", methods=['POST'])
def bet():
    amount = request.form['amount']
    userId = request.form['userId']
    pusher.trigger(game.gameId, 'action', {
        'action': 'bet',
        'user': userId,
        'amount': amount
    })

# create new game
def _start_game(gameId):
    game = query("SELECT * FROM game JOIN seat ON game.gameId = seat.gameId WHERE game.gameId = ?", [gameId])
    deck = []
    for card in CARDS:
        for suit in SUITS:
            deck.push({"card": card, "suit": suit})
    

    
    for seat in game:
        if seat['button']:
            button = seat['seatNumber']
    
    for seat in game:
        cards = [deck.pop(), deck.pop()]
        if seat['seat'] == button + 1 % 10:
            _bet(seat, 1)
        elif seat['seat'] == button + 2 % 10:
            _bet(seat, 2)
        pusher.trigger(game.gameId, 'hand', {'cards': cards})
    board = deck[-5]

if __name__ == "__main__":
    app.run()