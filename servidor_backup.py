from flask import Flask

app = Flask(__name__)

# O HTML é idêntico, exceto pelo data-server-id e pelo texto principal
HTML_CONTENT = """
<body data-server-id="backup">
    <h1>Servidor de Backup</h1>
    <p>Resposta do servidor de backup. O principal parece estar offline.</p>
    <p>Status da checagem: <span id="status">Aguardando...</span></p>

    <script>
        const currentServerId = document.body.getAttribute('data-server-id');
        async function checkServerStatus() {
            try {
                const response = await fetch('/proxy-status');
                const data = await response.json();
                const activeServer = data.active_server;
                document.getElementById('status').innerText = `Proxy reporta '${activeServer}' como ativo. Esta página é do '${currentServerId}'.`;
                if (activeServer !== currentServerId) {
                    document.getElementById('status').innerText = 'Detectada mudança de servidor! Recarregando...';
                    setTimeout(() => window.location.reload(), 1000);
                }
            } catch (error) {
                document.getElementById('status').innerText = 'Não foi possível contatar o proxy.';
                console.error('Erro ao checar status:', error);
            }
        }
        setInterval(checkServerStatus, 3000);
        checkServerStatus();
    </script>
</body>
"""
@app.route('/')
def index():
    return HTML_CONTENT

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)