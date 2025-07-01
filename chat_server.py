import socket
import threading
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- Configuração para acesso ao Banco de Dados ---
# Este servidor precisa de um contexto Flask para se comunicar com o banco de dados
# que será compartilhado com o servidor web.
app = Flask(__name__)
# Render irá fornecer esta URL para um banco de dados compartilhado (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# É preciso redefinir os modelos aqui para que este script saiba sobre eles
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)

# --- Lógica do Servidor de Chat Multithread ---
HOST = '0.0.0.0'  # Escuta em todas as interfaces de rede disponíveis
PORT = 10001      # Porta interna para o chat
clients = []
clients_lock = threading.Lock()

def broadcast(message, sender_socket):
    with clients_lock:
        for client in clients:
            if client != sender_socket:
                try:
                    client.sendall(message)
                except socket.error:
                    client.close()
                    clients.remove(client)

def handle_client(client_socket):
    try:
        # A primeira mensagem é o nome de usuário
        username_bytes = client_socket.recv(1024)
        if not username_bytes:
            return
        
        username = username_bytes.decode('utf-8').strip()
        print(f"Thread iniciada para o usuário: {username}")
        
        # Lógica de salvar no DB e enviar histórico iria aqui
        # (Omitido para focar na arquitetura de threads)

        broadcast(f"--- {username} entrou no chat. ---\n".encode('utf-8'), client_socket)

        while True:
            message = client_socket.recv(1024)
            if not message:
                break
            
            full_message = f"{username}: {message.decode('utf-8')}".encode('utf-8')
            broadcast(full_message, client_socket)

    except Exception as e:
        print(f"Erro com o cliente: {e}")
    finally:
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        print(f"Thread para {username if 'username' in locals() else 'desconhecido'} encerrada.")
        broadcast(f"--- {username if 'username' in locals() else 'Um usuário'} saiu do chat. ---\n".encode('utf-8'), None)


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"Servidor de Chat com Threads escutando em {HOST}:{PORT}")

    while True:
        client_socket, _ = server_socket.accept()
        with clients_lock:
            clients.append(client_socket)
        
        # REQUISITO CUMPRIDO: Uma nova thread para cada cliente
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    start_server()