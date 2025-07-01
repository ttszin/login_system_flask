# app.py
import os
import hashlib
import socket
import threading
from flask import Flask, request, redirect, url_for, render_template
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_sock import Sock
from waitress import serve  # Importamos o Waitress
from models import Usuario, Mensagem

# --- 1. CONFIGURAÇÃO GERAL ---
app = Flask(__name__)
# Usamos um banco de dados SQLite simples, que funcionará bem em um único serviço.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
sock = Sock(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 2. LÓGICA DO CHAT COM THREADS ---
clients = {}  # Usaremos um dicionário para mapear nome de usuário -> socket
clients_lock = threading.Lock()

def broadcast(message_bytes, sender_username):
    with clients_lock:
        for username, client_socket in clients.items():
            if username != sender_username:
                try:
                    client_socket.sendall(message_bytes)
                except:
                    # Se falhar, a limpeza será feita na thread do cliente
                    pass

def chat_client_thread(username, ws):
    """Esta é a thread que representa um cliente no backend."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # O cliente se conecta ao próprio processo do servidor, via localhost
        client_socket.connect(('127.0.0.1', 10001))
        
        with clients_lock:
            clients[username] = client_socket
        
        print(f"THREAD DE CHAT: {username} conectado.")
        broadcast(f"--- {username} entrou no chat ---\n".encode('utf-8'), username)

        # Loop para receber mensagens do navegador e enviar para outros
        while True:
            message_text = ws.receive()
            if message_text is None:
                break
            
            full_message = f"{username}: {message_text}\n".encode('utf-8')
            broadcast(full_message, username)
            
            # Salva no DB
            with app.app_context():
                user_obj = db.session.query(Usuario).filter_by(nome=username).first()
                if user_obj:
                    nova_mensagem = Mensagem(texto=message_text, autor=user_obj)
                    db.session.add(nova_mensagem)
                    db.session.commit()
    except Exception as e:
        print(f"Erro na thread de chat para {username}: {e}")
    finally:
        with clients_lock:
            if username in clients:
                del clients[username]
        client_socket.close()
        broadcast(f"--- {username} saiu do chat ---\n".encode('utf-8'), username)
        print(f"THREAD DE CHAT: {username} desconectado.")


@sock.route('/chat')
def chat_socket_bridge(ws):
    """Recebe a conexão WebSocket e dispara a thread de chat."""
    # A primeira mensagem é o nome de usuário
    username = ws.receive()
    
    # Instancia e inicia a thread do cliente de chat
    thread = threading.Thread(target=chat_client_thread, args=(username, ws))
    thread.daemon = True
    thread.start()
    
    # Esta thread apenas escuta o socket TCP e envia de volta para o navegador
    try:
        while thread.is_alive():
            with clients_lock:
                client_socket = clients.get(username)
            
            if client_socket:
                try:
                    # Espera por dados do servidor de broadcast
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    ws.send(data.decode('utf-8'))
                except:
                    break
    except Exception as e:
        print(f"Ponte WebSocket para {username} fechada: {e}")


# --- 3. MODELOS E ROTAS FLASK (Exatamente como antes) ---
class Usuario(db.Model, UserMixin):
    # ... (código completo do modelo Usuario)
    pass
# ... (código completo do modelo Mensagem e todas as rotas Flask: /login, etc.)
# ...

# --- 4. FUNÇÃO PARA INICIAR O SERVIDOR WEB ---
def run_web_server():
    # Usamos Waitress em vez do Gunicorn para servir a aplicação Flask
    print("--- Iniciando servidor web com Waitress na porta 10000 ---")
    serve(app, host='0.0.0.0', port=10000)

# --- PONTO DE ENTRADA PRINCIPAL ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Inicia o servidor web Flask em uma thread separada
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    print("--- O programa principal continua... pode adicionar a lógica do servidor TCP aqui se precisar ---")
    # Mantém o programa principal rodando para que as threads não morram
    while True:
        pass