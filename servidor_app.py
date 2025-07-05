import sys
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

# --- Configuração ---
app = Flask(__name__)
# Chave secreta para segurança da aplicação
app.config['SECRET_KEY'] = 'chave_super_secreta!'
# Configuração do banco de dados SQLite. Ele será um arquivo na mesma pasta.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Configura o SocketIO, permitindo requisições de outras origens (necessário para o nosso failover no cliente)
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
    # Busca todas as mensagens salvas no banco de dados
    messages = Message.query.order_by(Message.id).all()
    # Converte as mensagens para um formato de dicionário
    message_history = [msg.to_dict() for msg in messages]
    # Renderiza o template do chat, passando o histórico de mensagens
    return render_template('chat.html', history=message_history)

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
    # Cria um novo objeto Message com os dados recebidos
    new_message = Message(username=data['username'], text=data['text'])
    
    # Adiciona e salva a nova mensagem no banco de dados (Persistência)
    db.session.add(new_message)
    db.session.commit()
    
    # Retransmite a mensagem para TODOS os clientes conectados
    emit('new_message_broadcast', data, broadcast=True)

# --- Lógica de Inicialização ---
if __name__ == '__main__':
    # Garante que o número da porta seja fornecido ao iniciar o script
    if len(sys.argv) < 2:
        print("Erro: Forneça a porta como argumento. Ex: python servidor_app.py 5000")
        sys.exit(1)
    
    port = int(sys.argv[1])

    # Cria a tabela do banco de dados se ela não existir
    with app.app_context():
        db.create_all()

    print(f"--- INICIANDO SERVIDOR DE CHAT NA PORTA {port} ---")
    socketio.run(app, host='0.0.0.0', port=port)