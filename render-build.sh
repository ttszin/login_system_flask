#!/usr/bin/env bash
# Sair imediatamente se um comando falhar
set -o errexit

echo "Instalando dependências do Python..."
pip install -r requirements.txt

echo "Instalando o compilador TypeScript globalmente..."
npm install -g typescript

# Opcional: Se você tiver um arquivo tsconfig.json para compilar
# o app.ts para app.js, o comando iria aqui.
# Exemplo: tsc
# Como você já tem o app.js, este passo não é estritamente necessário agora.

echo "Build finalizado com sucesso!"