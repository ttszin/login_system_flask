import os
import hashlib
from flask import Flask, request, redirect, url_for, render_template
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_sock import Sock

# --- 1. CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
# O Render define a variável de ambiente DATABASE_URL. Se não existir, usa um sqlite local.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')

# Inicializa as extensões
db = SQLAlchemy(app)
sock = Sock(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Lista para manter todos os clientes WebSocket conectados
# Em um ambiente de produção real com múltiplos workers, seria necessário um backend como Redis.
# Para este projeto em um único processo, uma lista global é suficiente.
connected_clients = []

# --- 2. MODELOS DO BANCO DE DADOS (Models) ---
class Usuario(db.Model, login_user.UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(256), nullable=False)
    mensagens = db.relationship('Mensagem', backref='autor', lazy=True)

class Mensagem(db.Model):
    __tablename__ = 'mensagens'
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

# --- 3. LÓGICA DO CHAT (o antigo 'chat_core_server') ---
def broadcast(message_to_send):
    """Envia uma mensagem para todos os clientes conectados."""
    # Criamos uma cópia da lista para poder remover clientes desconectados com segurança
    for client in list(connected_clients):
        try:
            client.send(message_to_send)
        except Exception:
            # O cliente desconectou, remova-o da lista
            connected_clients.remove(client)

# --- 4. ROTA WEBSOCKET ---
@sock.route('/chat')
def chat_socket(ws):
    # 1. Adiciona o novo cliente à nossa lista de conexões
    connected_clients.append(ws)
    user_nome = "Anônimo" # Valor padrão

    try:
        # 2. O primeiro dado enviado pelo cliente é o nome de usuário
        user_nome = ws.receive(timeout=5)
        print(f"[*] Conexão WebSocket estabelecida para o usuário: {user_nome}")

        # 3. Notifica a todos que o usuário entrou
        broadcast(f"--- {user_nome} entrou na sala. ---")
        
        # 4. Envia o histórico de mensagens apenas para o novo cliente
        with app.app_context():
            ultimas_mensagens = db.session.query(Mensagem).order_by(Mensagem.timestamp.asc()).limit(50).all()
            for msg in ultimas_mensagens:
                history_line = f"(Histórico) {msg.autor.nome}: {msg.texto}"
                ws.send(history_line)
        ws.send(f"--- Bem-vindo, {user_nome}! ---")

        # 5. Loop para escutar por novas mensagens
        while True:
            message_text = ws.receive()
            if message_text:
                # Salva a mensagem no banco de dados e faz o broadcast
                with app.app_context():
                    usuario_obj = db.session.query(Usuario).filter_by(nome=user_nome).first()
                    if usuario_obj:
                        nova_mensagem = Mensagem(texto=message_text, autor=usuario_obj)
                        db.session.add(nova_mensagem)
                        db.session.commit()
                        
                        full_message = f"{user_nome}: {message_text}"
                        broadcast(full_message)

    except Exception as e:
        print(f"[*] Erro na conexão com {user_nome}: {e}")
    finally:
        # 6. Limpeza: Remove o cliente da lista e avisa que ele saiu
        if ws in connected_clients:
            connected_clients.remove(ws)
        broadcast(f"--- {user_nome} saiu da sala. ---")
        print(f"[*] Conexão WebSocket fechada para o usuário: {user_nome}")


# --- 5. ROTAS HTTP (o antigo 'main.py') ---
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
        # Verifica se o usuário já existe
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

# --- PONTO DE ENTRADA ---
# Criar o banco de dados se não existir, ao iniciar a aplicação
with app.app_context():
    db.create_all()