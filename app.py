import os
import hashlib
import asyncio
from flask import Flask, request, redirect, url_for, render_template
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sock import Sock
# ADICIONADO: Importar o 'db' do nosso arquivo
from db import db
# ADICIONADO: Importar os modelos da nossa fonte única da verdade
from models import Usuario, Mensagem

# --- 1. CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa as extensões com o app
db.init_app(app)
sock = Sock(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 2. CONFIGURAÇÃO DA PONTE (BRIDGE) ---
CHAT_SERVER_HOST = os.environ.get('CHAT_SERVER_HOST')
CHAT_SERVER_PORT = int(os.environ.get('CHAT_SERVER_PORT', 10001))

# REMOVIDO: As definições de modelos que estavam aqui foram removidas

# --- 4. PONTE WEBSOCKET ---
# (O código da ponte continua exatamente o mesmo de antes)
async def bridge_browser_to_tcp(ws, writer):
    """Lê do WebSocket (navegador) e escreve no TCP (servidor de chat)."""
    try:
        username = await ws.receive(timeout=5)
        writer.write(username.encode('utf-8') + b'\n')
        await writer.drain()
        async for msg in ws:
            writer.write(msg.encode('utf-8') + b'\n')
            await writer.drain()
    finally:
        writer.close()

async def bridge_tcp_to_browser(reader, ws):
    """Lê do TCP (servidor de chat) e escreve no WebSocket (navegador)."""
    try:
        while not reader.at_eof():
            data = await reader.readline()
            if data:
                await ws.send(data.decode('utf-8'))
            else:
                break
    finally:
        await ws.close()

@sock.route('/chat')
def chat_socket(ws):
    async def chat_handler():
        print(f"Nova conexão WebSocket. Conectando à ponte em {CHAT_SERVER_HOST}:{CHAT_SERVER_PORT}...")
        try:
            reader, writer = await asyncio.open_connection(CHAT_SERVER_HOST, CHAT_SERVER_PORT)
            browser_to_tcp_task = asyncio.create_task(bridge_browser_to_tcp(ws, writer))
            tcp_to_browser_task = asyncio.create_task(bridge_tcp_to_browser(reader, ws))
            await asyncio.gather(browser_to_tcp_task, tcp_to_browser_task)
        except Exception as e:
            print(f"Erro na ponte WebSocket: {e}")
    asyncio.run(chat_handler())

# --- 5. ROTAS HTTP E LÓGICA DE USUÁRIO ---
# (Todo o código das rotas Flask continua exatamente o mesmo de antes)
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

def hash_senha(txt):
    return hashlib.sha256(txt.encode('utf-8')).hexdigest()

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.nome)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form['nomeForm']
        senha = request.form['senhaForm']
        user = db.session.query(Usuario).filter_by(nome=nome, senha=hash_senha(senha)).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            return "Usuário ou senha incorretos", 401
    return render_template('login.html')

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form['nomeForm']
        if db.session.query(Usuario).filter_by(nome=nome).first():
            return "Este nome de usuário já está em uso.", 400
        senha = request.form['senhaForm']
        new_user = Usuario(nome=nome, senha=hash_senha(senha))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('cadastrar.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/healthz')
def health_check():
    return "OK", 200

# --- PONTO DE ENTRADA ---
with app.app_context():
    db.create_all()