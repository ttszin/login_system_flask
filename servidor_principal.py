from flask import Flask, jsonify

app = Flask(__name__)

# O HTML agora inclui um ID e um script para a verificação ativa
HTML_CONTENT = """
<body data-server-id="principal">
    <h1>Servidor Principal</h1>
    <p>Resposta do servidor principal.</p>
    <p>Status da checagem: <span id="status">Aguardando...</span></p>

    <script>
        // Pega o ID do servidor que serviu esta página
        const currentServerId = document.body.getAttribute('data-server-id');

        // Função para checar o status do proxy
        async function checkServerStatus() {
            try {
                const response = await fetch('/proxy-status');
                const data = await response.json();
                const activeServer = data.active_server;

                document.getElementById('status').innerText = `Proxy reporta '${activeServer}' como ativo. Esta página é do '${currentServerId}'.`;

                // Se o servidor ativo (segundo o proxy) for diferente do servidor que enviou esta página, recarregue.
                if (activeServer !== currentServerId) {
                    document.getElementById('status').innerText = 'Detectada mudança de servidor! Recarregando...';
                    // Espera um pouco para a mensagem ser visível e então recarrega
                    setTimeout(() => window.location.reload(), 1000);
                }
            } catch (error) {
                document.getElementById('status').innerText = 'Não foi possível contatar o proxy.';
                console.error('Erro ao checar status:', error);
            }
        }

        // Verifica o status a cada 3 segundos (3000 milissegundos)
        setInterval(checkServerStatus, 3000);
        // Roda uma vez assim que a página carrega
        checkServerStatus();
    </script>
</body>
"""

@app.route('/')
def index():
    return HTML_CONTENT

@app.route('/health')
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)