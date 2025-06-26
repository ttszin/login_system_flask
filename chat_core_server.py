# chat_core_server.py

import socket
import threading
import sys
from main import app
from models import Usuario, Mensagem
from db import db
# ==============================================================================
# PASSO 1: CONFIGURAÇÕES INICIAIS E DADOS COMPARTILHADOS
# ==============================================================================

# O endereço e porta do nosso servidor. Usamos '127.0.0.1' (localhost)
# porque apenas a nossa "Ponte WebSocket" vai se conectar a ele.
HOST = '127.0.0.1'
PORT = 9999 # Uma porta livre para a comunicação interna TCP

# Esta lista guardará todos os sockets dos clientes conectados.
# É um DADO COMPARTILHADO entre todas as threads.
clients = []

# O Lock é a ferramenta de sincronização mais importante.
# Ele vai garantir que apenas uma thread possa modificar a lista 'clients' por vez.
clients_lock = threading.Lock()

# ==============================================================================
# PASSO 2: FUNÇÃO DE BROADCAST (RETRANSMISSÃO)
# ==============================================================================

def broadcast(message: bytes, sender_socket: socket.socket):
    """
    Envia uma mensagem para todos os clientes conectados, exceto para o remetente.
    Esta função precisa ser 'thread-safe', ou seja, segura para ser usada por
    múltiplas threads ao mesmo tempo.
    """
    # 'with clients_lock:' adquire o lock no início do bloco e o libera no final.
    # Esta é a forma mais segura de usar locks.
    with clients_lock:
        for client_socket in clients:
            if client_socket != sender_socket:
                try:
                    client_socket.send(message)
                except socket.error:
                    # Se o envio falhar, o cliente provavelmente desconectou.
                    # Removemos o cliente da lista e fechamos o socket.
                    print("Erro ao enviar, removendo cliente.")
                    client_socket.close()
                    clients.remove(client_socket)

# ==============================================================================
# PASSO 3: FUNÇÃO QUE MANIPULA CADA CLIENTE (O CÓDIGO DA THREAD)
# ==============================================================================

def handle_client(client_socket: socket.socket):
    user = None # Armazenará o objeto Usuario do banco de dados
    try:
        client_file = client_socket.makefile('rw', encoding='utf-8', newline='\n')
        
        # A primeira linha é o nome de usuário
        username = client_file.readline().strip()
        if not username:
            raise ConnectionError("Cliente desconectou antes de se identificar.")

        # --- LÓGICA DE BANCO DE DADOS INICIA AQUI ---
        # Precisamos do contexto do app para fazer queries no banco de dados
        with app.app_context():
            # Encontra o objeto do usuário no banco de dados pelo nome
            user = db.session.query(Usuario).filter_by(nome=username).first()
            if not user:
                raise ConnectionError(f"Usuário '{username}' não encontrado no banco de dados.")

            print(f"Usuário '{user.nome}' (ID: {user.id}) conectou-se.")
            
            # 1. ENVIAR HISTÓRICO DE MENSAGENS PARA O NOVO USUÁRIO
            client_file.write(f"--- Bem-vindo ao chat, {user.nome}! Carregando histórico... ---\n")
            client_file.flush()

            # Busca as últimas 50 mensagens do banco de dados
            ultimas_mensagens = db.session.query(Mensagem).order_by(Mensagem.timestamp.desc()).limit(50).all()
            # Invertemos para enviar da mais antiga para a mais nova
            for msg in reversed(ultimas_mensagens):
                history_line = f"(Histórico) {msg.autor.nome}: {msg.texto}\n"
                client_file.write(history_line)
            client_file.flush()
            
        # 2. NOTIFICAR OS OUTROS QUE O USUÁRIO ENTROU
        broadcast(f"--- {user.nome} entrou na sala. ---\n".encode('utf-8'), client_socket)

        # Loop para receber e salvar novas mensagens
        for message_text in client_file:
            message_text = message_text.strip()
            if not message_text:
                continue

            # 3. SALVAR A NOVA MENSAGEM NO BANCO DE DADOS
            with app.app_context():
                nova_mensagem = Mensagem(texto=message_text, autor=user)
                db.session.add(nova_mensagem)
                db.session.commit()
            
            full_message = f"{user.nome}: {message_text}\n".encode('utf-8')
            broadcast(full_message, client_socket)

    except (OSError, ConnectionResetError, ConnectionError) as e:
        print(f"Conexão perdida ou erro: {e}")
    finally:
        username = user.nome if user else 'Um usuário desconhecido'
        print(f"Usuário '{username}' desconectou-se.")
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        broadcast(f"--- {username} saiu da sala. ---\n".encode('utf-8'), client_socket)

# ==============================================================================
# PASSO 4: FUNÇÃO PRINCIPAL QUE INICIA O SERVIDOR
# ==============================================================================

def main():
    """
    Função principal que configura o socket do servidor e aceita novas conexões.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"[*] Núcleo do Chat com Threads escutando em {HOST}:{PORT}")

    while True:
        # A chamada .accept() é bloqueante, ela espera até um novo cliente se conectar.
        client_socket, address = server_socket.accept()
        print(f"[*] Nova conexão aceita de {address[0]}:{address[1]}")

        # Adiciona o novo cliente à nossa lista compartilhada de forma segura
        with clients_lock:
            clients.append(client_socket)

        # Cria a nova thread para o cliente.
        # O 'target' é a função que a thread vai executar.
        # O 'args' é uma tupla com os argumentos para a função 'target'.
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True # Faz com que a thread não impeça o programa de fechar
        thread.start() # Inicia a execução da thread!

# Ponto de entrada do script
if __name__ == "__main__":
    main()