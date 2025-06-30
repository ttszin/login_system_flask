#!/usr/bin/env bash

echo "Iniciando o Núcleo do Chat (chat_core_server.py) em background..."
python chat_core_server.py &

echo "Aguardando 2 segundos para o núcleo iniciar..."
sleep 2

echo "Iniciando a Ponte WebSocket (websocket_bridge_server.py) em background..."
python websocket_bridge_server.py &

echo "Aguardando 2 segundos para a ponte iniciar..."
sleep 2

echo "Iniciando o Servidor Web Flask (main.py) em foreground..."
# Usamos Gunicorn para rodar o app Flask em produção
# O Render precisa que o servidor web escute na porta 10000
pip install gunicorn
gunicorn --bind 0.0.0.0:10000 main:app