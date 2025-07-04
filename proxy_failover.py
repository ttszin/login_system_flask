from flask import Flask, request, Response, jsonify # Adicionado jsonify
import requests

app = Flask(__name__)

PRIMARY_SERVER = 'http://127.0.0.1:5000'
BACKUP_SERVER = 'http://127.0.0.1:5001'

def get_active_server_and_status():
    """
    Verifica a saúde do servidor principal e retorna o servidor ativo
    e um nome de status ('principal' ou 'backup').
    """
    try:
        response = requests.get(f'{PRIMARY_SERVER}/health', timeout=1)
        if response.status_code == 200:
            return (PRIMARY_SERVER, 'principal')
    except requests.RequestException:
        pass
    return (BACKUP_SERVER, 'backup')

@app.route('/proxy-status')
def proxy_status():
    """Novo endpoint que informa ao cliente qual servidor está ativo."""
    _, status = get_active_server_and_status()
    return jsonify({'active_server': status})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """
    Atua como um proxy, encaminhando a requisição para o servidor apropriado.
    """
    target_server, status = get_active_server_and_status()
    print(f"Servidor ativo é o '{status}'. Encaminhando requisição.")

    try:
        # Nota: Não encaminhamos requisições para nosso próprio endpoint de status
        if path == 'proxy-status':
             return proxy_status()

        full_path = f'{target_server}/{path}'
        resp = requests.request(
            method=request.method,
            url=full_path,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    except requests.RequestException as e:
        return f'<h1>Erro de Gateway</h1><p>Não foi possível conectar a nenhum servidor. {e}</p>', 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)