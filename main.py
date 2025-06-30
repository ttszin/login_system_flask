from flask import Flask
from flask import request, redirect, url_for, render_template
from flask_login import LoginManager,login_user, login_required, logout_user, current_user
from db import db
from models import Usuario
import hashlib
import os # Importe o 'os'

app = Flask(__name__)
app.secret_key = 'teteucode'  # Chave secreta para proteger a sessão do usuário
lm = LoginManager(app)         #Variável que recebe as informações de login
lm.login_view = 'login'  # Define a rota de login para redirecionamento quando o usuário não estiver autenticado
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'     #database é o nome do banco de dados
db.init_app(app)

def hash(txt):
    """Função para hashear a senha do usuário"""
    return hashlib.sha256(txt.encode('utf-8')).hexdigest()  # Usando SHA-256 para hashear a senha

#Obtém as informações do usuário logado
@lm.user_loader
def user_loader(id):
    usuario = db.session.query(Usuario).filter_by(id=id).first()
    return usuario

#Rota do chat
@app.route('/')
@login_required # SÓ USUÁRIOS LOGADOS PODEM ACESSAR
def index():
    websocket_url = os.environ.get('WEBSOCKET_URL', 'ws://localhost:8765')
    return render_template('index.html', username=current_user.nome, websocket_url=websocket_url)
    
@app.route('/login', methods=['GET', 'POST'])  
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        nome = request.form['nomeForm']
        senha = request.form['senhaForm']

        user = db.session.query(Usuario).filter_by(nome=nome, senha=hash(senha)).first()
        if not user:
            return "Usuário ou senha incorretos"
        
        login_user(user)  # Realiza o login do usuário
        return redirect(url_for('index'))  # Redireciona para a página inicial após o login

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'GET':
        return render_template('cadastrar.html')
    elif request.method == 'POST':
        nome = request.form['nomeForm'] # Nome do usuário
        senha = request.form['senhaForm'] #Senha do usuário

        new_user = Usuario(nome=nome, senha=hash(senha))
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        #Retornando para a tela inicial
        return redirect(url_for('index'))
    
@app.route('/logout')
@login_required  # Decorador que exige que o usuário esteja logado para acessar a rota
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)