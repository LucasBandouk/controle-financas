
# Controle de Finanças - Entrega 1 (Flask + SQLite)

## Como rodar o projeto

### Backend (Flask)
1. Abra o VS Code e navegue até a pasta `backend`.
2. Crie um virtualenv (opcional): `python -m venv venv && source venv/bin/activate` (Linux/Mac) ou `venv\Scripts\activate` (Windows).
3. Instale dependências: `pip install flask flask-cors`.
4. Rode o servidor: `python app.py`.

O backend estará rodando em `http://127.0.0.1:5000`.

### Frontend
1. Abra o arquivo `frontend/index.html` no navegador.

### Usuário de teste
- **Usuário:** `test`
- **Senha:** `senha123`

### Funcionalidades da Entrega 1 (Sprint 1)
- Login de usuário.
- Cadastro de transações (receita/despesa).
- Listagem de transações.

### ✅ Entrega 2 (Sprint 2)
- Cadastro de categorias
- Filtro de transações por categoria

### ✅ Entrega 3 (Sprint 3)
- Cálculo automático de saldo financeiro
- Exibição de total de receitas, despesas e saldo no frontend
- Estilização do saldo (verde para positivo, vermelho para negativo)
