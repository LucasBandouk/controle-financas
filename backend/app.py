from flask import Flask, request, jsonify, make_response, Response
import sqlite3
from flask_cors import CORS
import hashlib
import csv
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "database.db"

# -------------------------
# Helpers - DB
# -------------------------
def get_conn():
    return sqlite3.connect(DB_NAME)

# -------------------------
# Inicialização / migrations simples
# -------------------------
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    senha TEXT)''')

    # categorias
    c.execute('''CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    usuario_id INTEGER)''')

    # transacoes (sem default com função)
    c.execute('''CREATE TABLE IF NOT EXISTS transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    valor REAL,
                    descricao TEXT,
                    tipo TEXT,
                    usuario_id INTEGER,
                    categoria_id INTEGER,
                    data TEXT,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY(categoria_id) REFERENCES categorias(id)
                )''')

    # usuário de teste
    hashed = hashlib.sha256("senha123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios (username, senha) VALUES (?, ?)", ("test", hashed))

    # garante colunas (migrations simples para dbs antigos)
    c.execute("PRAGMA table_info(transacoes)")
    cols = [row[1] for row in c.fetchall()]
    if "data" not in cols:
        c.execute("ALTER TABLE transacoes ADD COLUMN data TEXT")
    if "categoria_id" not in cols:
        c.execute("ALTER TABLE transacoes ADD COLUMN categoria_id INTEGER")

    conn.commit()
    conn.close()

def ensure_categories_column_and_table(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario_id INTEGER
        )
    """)
    cur.execute("PRAGMA table_info(transacoes)")
    cols = [row[1] for row in cur.fetchall()]
    if "categoria_id" not in cols:
        cur.execute("ALTER TABLE transacoes ADD COLUMN categoria_id INTEGER")
    if "data" not in cols:
        cur.execute("ALTER TABLE transacoes ADD COLUMN data TEXT")
    conn.commit()
    conn.close()

# -------------------------
# Rotas
# -------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida"}), 400
    username = data.get("username")
    senha_raw = data.get("senha", "")
    senha = hashlib.sha256(senha_raw.encode()).hexdigest()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM usuarios WHERE username=? AND senha=?", (username, senha))
    user = c.fetchone()
    conn.close()
    if user:
        return jsonify({"message": "Login bem-sucedido", "usuario_id": user[0]})
    return jsonify({"error": "Credenciais inválidas"}), 401

# -------------------------------
# Categorias
# -------------------------------
@app.route("/categorias", methods=["POST"])
def add_categoria():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida"}), 400
    nome = data.get("nome")
    usuario_id = data.get("usuario_id")
    if not nome or usuario_id is None:
        return jsonify({"error": "nome e usuario_id são obrigatórios"}), 400

    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categorias (nome, usuario_id) VALUES (?, ?)", (nome, usuario_id))
    categoria_id = c.lastrowid

    # Vincula transações antigas que contenham o nome na descrição (opcional)
    c.execute("""
        UPDATE transacoes
        SET categoria_id=?
        WHERE usuario_id=? AND categoria_id IS NULL AND descricao LIKE ?
    """, (categoria_id, usuario_id, f"%{nome}%"))

    conn.commit()
    conn.close()
    return jsonify({"message": "Categoria adicionada com sucesso e transações antigas vinculadas!", "categoria_id": categoria_id})

@app.route("/categorias/<int:usuario_id>", methods=["GET"])
def get_categorias(usuario_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nome FROM categorias WHERE usuario_id=?", (usuario_id,))
    categorias = [{"id": row[0], "nome": row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(categorias)

# -------------------------------
# Transações
# -------------------------------
@app.route("/transacoes", methods=["POST"])
def add_transacao():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida"}), 400
    valor = data.get("valor")
    descricao = data.get("descricao", "")
    tipo = data.get("tipo")
    usuario_id = data.get("usuario_id")
    categoria_id = data.get("categoria_id")
    data_transacao = data.get("data")
    if not data_transacao:
        data_transacao = datetime.now().strftime("%Y-%m-%d")
    if valor is None or tipo is None or usuario_id is None:
        return jsonify({"error": "valor, tipo e usuario_id são obrigatórios"}), 400

    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO transacoes (valor, descricao, tipo, usuario_id, categoria_id, data)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (valor, descricao, tipo, usuario_id, categoria_id, data_transacao))
    conn.commit()
    conn.close()
    return jsonify({"message": "Transação adicionada com sucesso"})

@app.route("/transacoes/<int:usuario_id>", methods=["GET"])
def get_transacoes(usuario_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT t.id, t.valor, t.descricao, t.tipo, c.nome AS categoria, t.data
                 FROM transacoes t
                 LEFT JOIN categorias c ON t.categoria_id = c.id
                 WHERE t.usuario_id=?
                 ORDER BY t.data DESC""", (usuario_id,))
    transacoes = [{"id": row[0], "valor": row[1], "descricao": row[2], "tipo": row[3], "categoria": row[4], "data": row[5]} for row in c.fetchall()]
    conn.close()
    return jsonify(transacoes)

@app.route("/transacoes/<int:usuario_id>/categoria/<int:categoria_id>", methods=["GET"])
def get_transacoes_por_categoria(usuario_id, categoria_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.valor, t.descricao, t.tipo, c.nome AS categoria, t.data
        FROM transacoes t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id=? AND t.categoria_id=?
        ORDER BY t.data DESC
    """, (usuario_id, categoria_id))
    transacoes = [{"id": row[0], "valor": row[1], "descricao": row[2], "tipo": row[3], "categoria": row[4], "data": row[5]} for row in c.fetchall()]
    conn.close()
    return jsonify(transacoes)

# -------------------------------
# Resumo financeiro
# -------------------------------
@app.route("/resumo/<int:usuario_id>", methods=["GET"])
def resumo_financeiro(usuario_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT SUM(valor) FROM transacoes WHERE usuario_id=? AND tipo='receita'""", (usuario_id,))
    total_receitas = c.fetchone()[0] or 0.0
    c.execute("""SELECT SUM(valor) FROM transacoes WHERE usuario_id=? AND tipo='despesa'""", (usuario_id,))
    total_despesas = c.fetchone()[0] or 0.0
    conn.close()
    saldo = total_receitas - total_despesas
    return jsonify({"total_receitas": round(total_receitas, 2), "total_despesas": round(total_despesas, 2), "saldo": round(saldo, 2)})

# -------------------------------
# Resumo mensal (JSON) - usado para gráficos
# -------------------------------
@app.route("/resumo_mensal/<int:usuario_id>", methods=["GET"])
def resumo_mensal(usuario_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("PRAGMA table_info(transacoes)")
    cols = [row[1] for row in c.fetchall()]
    if 'data' not in cols:
        conn.close()
        return jsonify({"error": "Coluna 'data' ausente. Rode init_db/ensure migrations."}), 500

    c.execute("""
        SELECT strftime('%Y-%m', data) AS mes, tipo, SUM(valor)
        FROM transacoes
        WHERE usuario_id=?
        GROUP BY mes, tipo
        ORDER BY mes
    """, (usuario_id,))
    resultado = c.fetchall()
    conn.close()

    resumo = {}
    for mes, tipo, total in resultado:
        resumo.setdefault(mes, {"receitas": 0.0, "despesas": 0.0})
        if tipo == "receita":
            resumo[mes]["receitas"] = float(total or 0.0)
        else:
            resumo[mes]["despesas"] = float(total or 0.0)
    return jsonify(resumo)

# -------------------------------
# Relatório mensal (CSV) - conforme front
# Endpoint esperado pelo front: /relatorio_mensal/<usuario_id>?ano=YYYY&mes=MM
# -------------------------------
@app.route("/relatorio_mensal/<int:usuario_id>", methods=["GET"])
def relatorio_mensal_csv(usuario_id):
    ano = request.args.get("ano")
    mes = request.args.get("mes")
    if not ano or not mes:
        return jsonify({"error": "Ano e mês são obrigatórios (params 'ano' e 'mes')"}), 400

    mes_z = mes.zfill(2)
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.valor, t.descricao, t.tipo, COALESCE(c.nome, '') as categoria, t.data
        FROM transacoes t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id=? AND strftime('%Y', t.data)=? AND strftime('%m', t.data)=?
        ORDER BY t.data ASC
    """, (usuario_id, ano, mes_z))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Valor", "Descrição", "Tipo", "Categoria", "Data"])
    for row in rows:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    filename = f"relatorio_{usuario_id}_{ano}_{mes_z}.csv"
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

# -------------------------------
# Exportar todas as transações (CSV)
# -------------------------------
@app.route("/exportar_transacoes/<int:usuario_id>", methods=["GET"])
def exportar_transacoes(usuario_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.valor, t.descricao, t.tipo, COALESCE(c.nome, '') as categoria, t.data
        FROM transacoes t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE t.usuario_id=?
        ORDER BY t.data DESC
    """, (usuario_id,))
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Valor", "Descrição", "Tipo", "Categoria", "Data"])
    for row in rows:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    filename = f"transacoes_{usuario_id}.csv"
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

# -------------------------------
# Inicialização do servidor
# -------------------------------
if __name__ == "__main__":
    init_db()
    ensure_categories_column_and_table(DB_NAME)
    app.run(debug=True)
