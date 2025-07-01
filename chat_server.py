import socket
import threading
import os
import sys
from flask import Flask
from db import db
from models import Usuario, Mensagem

# --- 1. CONFIGURAÇÃO INICIAL ---
# Esta seção configura um contexto Flask mínimo apenas para que este script
# possa se comunicar com o banco de dados compartilhado.
app = Flask(__name__)
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("ERRO FATAL: DATABASE_URL não foi encontrada.")
    sys.exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
print("--- Configuração do Banco de Dados concluída. ---")

# --- 2. LÓGICA DO SERVIDOR DE CHAT MULTITHREAD ---
HOST = '0.0.0.0'  # Escuta em todas as interfaces de rede
PORT = 10001      # Porta interna para a comunicação
clients = []
clients_lock = threading.Lock()

def broadcast(message, sender_socket):
    """Envia uma mensagem para todos os clientes conectados, exceto o remetente."""
    with clients_lock:
        for client in list(clients):
            if client != sender_socket:
                try:
                    client.sendall(message)
                except socket.error:
                    # Se o envio falhar, remove o cliente da lista.
                    clients.remove(client)
                    client.close()

def handle_client(client_socket):
    """
    Esta função é executada em uma thread separada para cada cliente.
    Ela gerencia o ciclo de vida de uma conexão de usuário.
    """
    username = None
    user_obj = None
    try:
        # A primeira mensagem recebida é sempre o nome de usuário.
        username_bytes = client_socket.recv(1024)
        if not username_bytes: return
        
        username = username_bytes.decode('utf-8').strip()

        # Usamos o contexto do app para fazer queries no banco de dados.
        with app.app_context():
            user_obj = db.session.query(Usuario).filter_by(nome=username).first()
        
        if not user_obj:
            print(f"Usuário '{username}' não encontrado. Encerrando thread.")
            return

        print(f"Thread iniciada para o usuário: {user_obj.nome}")
        broadcast(f"--- {username} entrou no chat. ---\n".encode('utf-8'), client_socket)

        # Loop principal para receber e processar as mensagens do cliente.
        while True:
            message_bytes = client_socket.recv(1024)
            if not message_bytes: break # Conexão fechada pelo cliente
            
            message_text = message_bytes.decode('utf-8').strip()
            
            # Salva a mensagem recebida no banco de dados.
            with app.app_context():
                # Re-buscamos o autor para garantir que ele está na sessão atual do DB.
                autor_obj = db.session.get(Usuario, user_obj.id)
                nova_mensagem = Mensagem(texto=message_text, autor=autor_obj)
                db.session.add(nova_mensagem)
                db.session.commit()

            # Retransmite a mensagem para todos os outros clientes.
            full_message = f"{username}: {message_text}\n".encode('utf-8')
            broadcast(full_message, client_socket)

    except Exception as e:
        print(f"Erro na thread do cliente {username}: {e}")
    finally:
        # Limpeza: remove o cliente da lista e avisa aos outros que ele saiu.
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        if username:
            print(f"Thread para {username} encerrada.")
            broadcast(f"--- {username} saiu do chat. ---\n".encode('utf-8'), None)

def start_server():
    """Função principal que inicia o servidor e aceita novas conexões."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"Servidor de Chat com Threads escutando em {HOST}:{PORT}")

    while True:
        # Bloqueia até uma nova conexão chegar.
        client_socket, _ = server_socket.accept()
        with clients_lock:
            clients.append(client_socket)
        
        # REQUISITO CUMPRIDO: Uma nova thread é criada para cada cliente.
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    start_server()
