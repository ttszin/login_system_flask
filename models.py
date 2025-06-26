from db import db
from flask_login import UserMixin   # Importando UserMixin para integrar com Flask-Login para a classe seja identificada como uma classe
                                    #de usuário pelo sistema de login do flask
from sqlalchemy.sql import func # Usaremos para o timestamp


class Mensagem(db.Model):
    __tablename__ = 'mensagens'

    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(500), nullable=False)
    # Define o timestamp para ser a data e hora atuais por padrão quando uma mensagem é criada
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Chave estrangeira para ligar a mensagem a um usuário
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    def __repr__(self):
        return f'<Mensagem {self.id}>'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String())

    # Relação: Permite acessar todas as mensagens de um usuário com 'usuario.mensagens'
    # E acessar o autor de uma mensagem com 'mensagem.autor'
    mensagens = db.relationship('Mensagem', backref='autor', lazy=True)