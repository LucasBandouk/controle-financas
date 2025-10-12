from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import hashlib

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# -------------------------------
# Inicialização do banco de dados
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    senha TEXT)''')
    # Tabela de transações
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

# -------------------------------
# Nova função: garantir tabela de categorias e coluna
# -------------------------------
def ensure_categories_column_and_table(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Cria tabela de categorias se não existir
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario_id INTEGER
        )
    """)

    # Checa se coluna categoria_id existe em transacoes
    cur.execute("PRAGMA table_info(transacoes)")
    cols = [row[1] for row in cur.fetchall()]
    if 'categoria_id' not in cols:
        cur.execute("ALTER TABLE transacoes ADD COLUMN categoria_id INTEGER")

    conn.commit()
    conn.close()

# -------------------------------
# Rotas do sistema
# -------------------------------
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

# -------------------------------
# Rotas de Categorias (nova funcionalidade)
# -------------------------------
@app.route("/categorias", methods=["POST"])
def add_categoria():
    data = request.get_json()
    nome = data.get("nome")
    usuario_id = data.get("usuario_id")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO categorias (nome, usuario_id) VALUES (?, ?)", (nome, usuario_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Categoria adicionada com sucesso!"})

@app.route("/categorias/<int:usuario_id>", methods=["GET"])
def get_categorias(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, nome FROM categorias WHERE usuario_id=?", (usuario_id,))
    categorias = [{"id": row[0], "nome": row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(categorias)

# -------------------------------
# Rotas de Transações (ajustadas para incluir categoria_id)
# -------------------------------
@app.route("/transacoes", methods=["POST"])
def add_transacao():
    data = request.get_json()
    valor = data.get("valor")
    descricao = data.get("descricao")
    tipo = data.get("tipo")
    usuario_id = data.get("usuario_id")
    categoria_id = data.get("categoria_id")  # novo campo (pode ser None)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO transacoes (valor, descricao, tipo, usuario_id, categoria_id)
                 VALUES (?, ?, ?, ?, ?)""",
              (valor, descricao, tipo, usuario_id, categoria_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Transação adicionada com sucesso"})

@app.route("/transacoes/<int:usuario_id>", methods=["GET"])
def get_transacoes(usuario_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""SELECT t.id, t.valor, t.descricao, t.tipo, c.nome AS categoria
                 FROM transacoes t
                 LEFT JOIN categorias c ON t.categoria_id = c.id
                 WHERE t.usuario_id=?""", (usuario_id,))
    transacoes = [{"id": row[0], "valor": row[1], "descricao": row[2],
                   "tipo": row[3], "categoria": row[4]} for row in c.fetchall()]
    conn.close()
    return jsonify(transacoes)

# -------------------------------
# Inicialização do servidor
# -------------------------------
if __name__ == "__main__":
    init_db()
    ensure_categories_column_and_table(DB_NAME)
    app.run(debug=True)
