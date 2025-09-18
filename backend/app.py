
from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import hashlib

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    senha TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    valor REAL,
                    descricao TEXT,
                    tipo TEXT,
                    usuario_id INTEGER,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
    # Usuário padrão
    c.execute("INSERT OR IGNORE INTO usuarios (username, senha) VALUES (?, ?)",
              ("test", hashlib.sha256("senha123".encode()).hexdigest()))
    conn.commit()
    conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    senha = hashlib.sha256(data.get("senha").encode()).hexdigest()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM usuarios WHERE username=? AND senha=?", (username, senha))
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({"message": "Login bem-sucedido", "usuario_id": user[0]})
    return jsonify({"error": "Credenciais inválidas"}), 401

@app.route("/transacoes", methods=["POST"])
def add_transacao():
    data = request.get_json()
    valor = data.get("valor")
    descricao = data.get("descricao")
    tipo = data.get("tipo")
    usuario_id = data.get("usuario_id")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO transacoes (valor, descricao, tipo, usuario_id) VALUES (?, ?, ?, ?)",
              (valor, descricao, tipo, usuario_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Transação adicionada com sucesso"})

@app.route("/transacoes/<int:usuario_id>", methods=["GET"])
def get_transacoes(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, valor, descricao, tipo FROM transacoes WHERE usuario_id=?", (usuario_id,))
    transacoes = [{"id": row[0], "valor": row[1], "descricao": row[2], "tipo": row[3]} for row in c.fetchall()]
    conn.close()
    return jsonify(transacoes)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
