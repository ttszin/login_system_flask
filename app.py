import os
import hashlib
import socket
import threading
from flask import Flask, request, redirect, url_for, render_template
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sock import Sock
from db import db
from models import Usuario, Mensagem
from gevent import monkey
monkey.patch_all()

# --- 1. CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
sock = Sock(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 2. CONFIGURAÇÃO DA PONTE (BRIDGE) ---
CHAT_SERVER_HOST = os.environ.get('CHAT_SERVER_HOST')
CHAT_SERVER_PORT = int(os.environ.get('CHAT_SERVER_PORT', 10001))

# --- 3. PONTE WEBSOCKET COM THREADS (LÓGICA CORRIGIDA) ---
@sock.route('/chat')
def chat_socket(ws):
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((CHAT_SERVER_HOST, CHAT_SERVER_PORT))
        print("Ponte conectada com sucesso ao chat-server.")
    except Exception as e:
        print(f"PONTE FALHOU AO CONECTAR COM CHAT-SERVER: {e}")
        ws.close()
        return

    stop_event = threading.Event()

    # THREAD 1: Lê do navegador (WebSocket) e envia para o servidor de chat (TCP)
    def browser_to_tcp():
        try:
            # O ws.receive() agora vai bloquear até uma mensagem chegar, sem timeout.
            # O gevent cuida para que isso não trave o servidor.
            while not stop_event.is_set():
                data = ws.receive()
                if data is None: # Conexão fechada pelo navegador
                    break
                tcp_socket.sendall(data.encode('utf-8') + b'\n')
        except Exception as e:
            print(f"Conexão navegador->servidor fechada: {e}")
        finally:
            stop_event.set() # Sinaliza para a outra thread parar

    # THREAD 2: Lê do servidor de chat (TCP) e envia para o navegador (WebSocket)
    def tcp_to_browser():
        try:
            while not stop_event.is_set():
                data = tcp_socket.recv(4096)
                if not data: # Conexão fechada pelo servidor de chat
                    break
                ws.send(data.decode('utf-8'))
        except Exception as e:
            print(f"Conexão servidor->navegador fechada: {e}")
        finally:
            stop_event.set()

    # Inicia as duas threads para fazer a ponte
    b2t = threading.Thread(target=browser_to_tcp)
    t2b = threading.Thread(target=tcp_to_browser)
    b2t.daemon = True
    t2b.daemon = True
    
    b2t.start()
    t2b.start()
    
    # Mantém a rota viva enquanto as threads estiverem rodando
    stop_event.wait()
    
    tcp_socket.close()
    ws.close()
    print("Ponte WebSocket encerrada.")

# --- 4. ROTAS HTTP E LÓGICA DE USUÁRIO ---
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