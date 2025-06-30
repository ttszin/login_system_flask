# websocket_bridge_server.py (VERSÃO CORRIGIDA)

import asyncio
import websockets
import socket
import os # Importe o 'os'

# O host do core virá de uma variável de ambiente. Se não existir, usa localhost como padrão.
CORE_SERVER_HOST = os.environ.get('CORE_SERVER_HOST', '127.0.0.1')
CORE_SERVER_PORT = 9999

# ############################################################### #
# A CORREÇÃO PRINCIPAL ESTÁ NA FUNÇÃO listen_to_core ABAIXO     #
# ############################################################### #
async def listen_to_core(reader: asyncio.StreamReader, websocket: websockets.WebSocketServerProtocol):
    """Escuta por mensagens do Núcleo do Chat e as envia para o navegador via WebSocket."""
    while True:
        try:
            # CORRIGIDO: Usamos reader.readline() para ler uma linha completa,
            # exatamente como o Núcleo envia (com \n no final).
            data = await reader.readline()
            if not data:
                print("Ponte: Conexão com o núcleo do chat foi fechada.")
                break
            
            # Envia os dados decodificados para o cliente do navegador
            await websocket.send(data.decode('utf-8'))
        except (ConnectionResetError, websockets.exceptions.ConnectionClosed, asyncio.IncompleteReadError):
            print("Ponte: Conexão com o navegador foi perdida (no listener do core).")
            break

async def listen_to_browser(websocket: websockets.WebSocketServerProtocol, writer: asyncio.StreamWriter):
    """Escuta por mensagens do navegador (WebSocket) e as envia para o Núcleo do Chat via TCP."""
    try:
        async for message in websocket:
            # Adicionamos \n se não houver, para garantir que o readline do servidor funcione
            if not message.endswith('\n'):
                message += '\n'
            writer.write(message.encode('utf-8'))
            await writer.drain()
    except websockets.exceptions.ConnectionClosedError:
        print(f"Ponte: Cliente {websocket.remote_address} desconectou.")
    finally:
        writer.close()

async def bridge_handler(websocket: websockets.WebSocketServerProtocol, path=None):
    print(f"Ponte: Nova conexão WebSocket de {websocket.remote_address}")
    try:
        reader, writer = await asyncio.open_connection(CORE_SERVER_HOST, CORE_SERVER_PORT)
        listen_core_task = asyncio.create_task(listen_to_core(reader, websocket))
        listen_browser_task = asyncio.create_task(listen_to_browser(websocket, writer))
        
        done, pending = await asyncio.wait(
            [listen_core_task, listen_browser_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        print(f"Ponte: Encerrando conexão para {websocket.remote_address}.")
    except ConnectionRefusedError:
        print("[ERRO FATAL] Ponte: Não foi possível conectar ao Núcleo do Chat.")
        await websocket.close(code=1011, reason="Servidor de chat indisponível")
    except Exception as e:
        print(f"Ponte: Ocorreu um erro inesperado na ponte: {e}")

async def main():
    async with websockets.serve(bridge_handler, "localhost", 8765):
        print("[*] Ponte WebSocket iniciada em ws://localhost:8765")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Ponte: Servidor encerrado.")