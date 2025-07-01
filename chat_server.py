import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 10001

def handle_client(client_socket):
    """
    Função simples que apenas mantém a conexão viva e responde a pings.
    """
    print(f"Thread de diagnóstico iniciada para um novo cliente.")
    try:
        client_socket.sendall(b"--- Conectado ao Servidor de Teste de Rede ---\n")
        while True:
            # Mantém a conexão aberta
            time.sleep(10)
    except Exception as e:
        print(f"Conexão de diagnóstico encerrada: {e}")
    finally:
        client_socket.close()

def start_server():
    """
    Inicia o servidor de teste.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # A opção SO_REUSEADDR ajuda a evitar o erro "Address already in use" durante reinicializações rápidas
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"--- SERVIDOR DE TESTE DE REDE escutando em {HOST}:{PORT} ---")

    while True:
        client_socket, _ = server_socket.accept()
        print("--- Conexão de teste recebida! Iniciando thread... ---")
        thread = threading.Thread(target=handle_client, args=(client_socket,))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    start_server()