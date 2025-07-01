import socket
import threading
import os
import sys
from flask import Flask
from db import db
from models import Usuario, Mensagem

# --- DEBUGGING INICIAL ---
# Esta é a primeira coisa que o script faz.
print("--- INICIANDO SCRIPT chat_server.py ---")
db_url_from_env = os.environ.get('DATABASE_URL')

if db_url_from_env:
    print(f"Variável DATABASE_URL encontrada com sucesso.")
    # Não vamos imprimir a URL completa por segurança, apenas confirmar que ela existe.
else:
    print("!!! ERRO CRÍTICO: Variável de ambiente DATABASE_URL não foi encontrada pelo script. !!!")
    sys.exit("Encerrando devido à falta da DATABASE_URL.") # Encerra o script se a variável não existe

print("--- DEBUGGING COMPLETO, INICIANDO CONFIGURAÇÃO DO APP ---")
# --- FIM DO DEBUGGING ---


# --- Configuração para acesso ao Banco de Dados ---
app = Flask(__name__)
# Usamos a variável que acabamos de verificar
app.config['SQLALCHEMY_DATABASE_URI'] = db_url_from_env
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- Lógica do Servidor de Chat Multithread ---
HOST = '0.0.0.0'
PORT = 10001
clients = []
clients_lock = threading.Lock()

# (O resto do código continua exatamente o mesmo de antes)
def broadcast(message, sender_socket):
    with clients_lock:
        for client in clients:
            if client != sender_socket:
                try:
                    client.sendall(message)
                except socket.error:
                    clients.remove(client)
                    client.close()

def handle_client(client_socket):
    username = None
    user_obj = None
    try:
        username_bytes = client_socket.recv(1024)
        if not username_bytes:
            return
        
        username = username_bytes.decode('utf-8').strip()

        with app.app_context():
            user_obj = db.session.query(Usuario).filter_by(nome=username).first()
        
        if not user_obj:
            print(f"Usuário '{username}' não encontrado. Encerrando thread.")
            return

        print(f"Thread iniciada para o usuário: {user_obj.nome} (ID: {user_obj.id})")
        broadcast(f"--- {username} entrou no chat. ---\n".encode('utf-8'), client_socket)

        while True:
            message_bytes = client_socket.recv(1024)
            if not message_bytes:
                break
            
            message_text = message_bytes.decode('utf-8').strip()
            
            with app.app_context():
                nova_mensagem = Mensagem(texto=message_text, autor=user_obj)
                db.session.add(nova_mensagem)
                db.session.commit()

            full_message = f"{username}: {message_text}\n".encode('utf-8')
            broadcast(full_message, client_socket)

    except Exception as e:
        print(f"Erro com o cliente {username}: {e}")
    finally:
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        
        if username:
            print(f"Thread para {username} encerrada.")
            broadcast(f"--- {username} saiu do chat. ---\n".encode('utf-8'), None)

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"Servidor de Chat com Threads escutando em {HOST}:{PORT}")

    while True:
        client_socket, _ = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    start_server()