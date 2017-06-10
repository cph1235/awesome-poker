from flask import Flask, render_template, request, g
from pusher import Pusher
import sqlite3
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
STAGE = Enum("STAGE", "PREFLOP FLOP TURN RIVER SHOWDOWN")
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

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def update_db(query, args=()):
    cur = get_db().execute

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
    username = request.form['username']
    password = request.form['password']
    chip = request.form['chip']

    if not query_db("SELECT * FROM user WHERE username = ?", [username], one=True):
        update_db("INSERT INTO user (username, password, chip) VALUES (?, ?, ?)", [username, password, chip])
    table = query_db("SELECT * FROM table WHERE player < 9 ")
    if not table:
        result = update_db("INSERT INTO table (tableName, status) VALUES (?, ?)", ('TABLE1', 'WAITING'))
    return {username: username, chip: chip, table: table.tableId}

@app.route("/join", methods=['POST'])
def join():
    tableId = request.form['tableId']
    userId = request.form['userId']
    chip = request.form['chip']
    seat = request.form['seat']

    query_db("INSERT INTO player (userId, tableId, chip, seat) VALUES (?, ?, ?, ?)", ())

    table = query_db("SELECT * FROM table WHERE tableId = ?")
    if table['status'] == STAGE.WAIT:
        start_game()
    

@app.route("/game", methods=['POST'])
def game():
    players = request.form['players']
    stage = request.form['stage']
    pusher.trigger('poker-channel', 'start', {'message': 'hello :)'})

if __name__ == "__main__":
    app.run()