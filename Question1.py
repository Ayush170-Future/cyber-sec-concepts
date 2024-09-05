import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'bank.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = query_db('SELECT * FROM users WHERE username = ? AND password = ?', [username, password], one=True)
    if user:
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401


@app.route('/transfer_funds', methods=['POST'])
def transfer_funds():
    data = request.get_json()
    source_account = data.get('source_account')
    destination_account = data.get('destination_account')
    amount = data.get('amount')

    if not source_account or not destination_account or not amount:
        return jsonify({"message": "Missing parameters"}), 400

    source = query_db('SELECT balance FROM accounts WHERE account_number = ?', [source_account], one=True)
    destination = query_db('SELECT balance FROM accounts WHERE account_number = ?', [destination_account], one=True)


    if source < amount:
        return jsonify({"message": "Insufficient funds"}), 400

    db = get_db()
    db.execute('UPDATE accounts SET balance = balance - ? WHERE account_number = ?', [amount, source_account])
    db.execute('UPDATE accounts SET balance = balance + ? WHERE account_number = ?', [amount, destination_account])
    db.commit()

    updated_source = query_db('SELECT balance FROM accounts WHERE account_number = ?', [source_account], one=True)
    updated_destination = query_db('SELECT balance FROM accounts WHERE account_number = ?', [destination_account], one=True)

    return jsonify({
        "message": "Transfer successful",
        "source_account": source_account,
        "destination_account": destination_account,
        "source_balance": updated_source[0],
        "destination_balance": updated_destination[0]
    }), 200