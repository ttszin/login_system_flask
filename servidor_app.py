import sys
import os
import signal
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

# --- Configuração ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_super_secreta!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Modelo do Banco de Dados ---
class Message(db.Model):
    """Define a estrutura da tabela de mensagens no banco de dados."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    text = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        """Converte o objeto Message para um dicionário, útil para enviar via JSON."""
        return {'username': self.username, 'text': self.text}

# --- Rotas HTTP ---
@app.route('/')
def index():
    """Rota principal que serve a página do chat."""
    messages = Message.query.order_by(Message.id).all()
    message_history = [msg.to_dict() for msg in messages]
    return render_template('chat.html', history=message_history)

# --- NOVOS ENDPOINTS DE CONTROLE ---
@app.route('/health')
def health_check():
    """Um endpoint simples para verificar se o servidor está no ar."""
    return 'OK', 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Endpoint que desliga o servidor.
    O systemd (com Restart=always) irá reiniciá-lo automaticamente.
    """
    print("Recebido pedido de desligamento. Encerrando o processo...")
    # Envia um sinal de interrupção para o próprio processo, simulando um Ctrl+C
    os.kill(os.getpid(), signal.SIGINT)
    return 'Servidor encerrando...', 200

# --- Eventos do Socket.IO ---
@socketio.on('connect')
def handle_connect():
    """Loga uma mensagem quando um novo cliente se conecta."""
    print('Novo cliente conectado!')

@socketio.on('send_message')
def handle_send_message(data):
    """
    Recebe uma nova mensagem, salva no banco de dados e a retransmite para todos.
    """
    print(f"Mensagem recebida: {data}")
    new_message = Message(username=data['username'], text=data['text'])
    
    db.session.add(new_message)
    db.session.commit()
    
    emit('new_message_broadcast', data, broadcast=True)

# Cria a tabela do banco de dados se ela não existir, antes de iniciar o app.
# Isso garante que o DB seja criado mesmo quando rodando com Gunicorn.
with app.app_context():
    db.create_all()

# --- Lógica de Inicialização para teste local ---
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Erro: Forneça a porta como argumento. Ex: python servidor_app.py 5000")
        sys.exit(1)
    
    port = int(sys.argv[1])

    print(f"--- INICIANDO SERVIDOR DE CHAT NA PORTA {port} ---")
    socketio.run(app, host='0.0.0.0', port=port)
