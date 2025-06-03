from db import db
from flask_login import UserMixin   # Importando UserMixin para integrar com Flask-Login para a classe seja identificada como uma classe
                                    #de usuário pelo sistema de login do flask

class Usuario(UserMixin,db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)
    senha = db.Column(db.String())