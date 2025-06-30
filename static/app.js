// static/app.js

// 1. SELECIONANDO OS ELEMENTOS DO "PALCO" (HTML)
const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");

// 2. CONSTRUINDO A URL DO WEBSOCKET DINAMICAMENTE
const socketProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const socketUrl = `${socketProtocol}//${window.location.host}/chat`;
const ws = new WebSocket(socketUrl);

// 3. LÓGICA DO WEBSOCKET
ws.onopen = function () {
    console.log("Conectado ao servidor de Chat!");
    // A primeira mensagem que enviamos é o nome do nosso usuário para identificação
    if (authenticated_user) {
        ws.send(authenticated_user);
    }
};

ws.onmessage = function (event) {
    const message = event.data;
    // Adiciona uma quebra de linha se não for a primeira mensagem
    if (messagesDiv.textContent.length > 0) {
        messagesDiv.textContent += "\n" + message;
    } else {
        messagesDiv.textContent = message;
    }
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

ws.onclose = function () {
    messagesDiv.textContent += "\n--- Conexão com o servidor perdida. Por favor, atualize a página. ---\n";
};

ws.onerror = function (error) {
    console.error('WebSocket Error:', error);
    messagesDiv.textContent += "\n--- Ocorreu um erro na conexão. ---\n";
};

// 4. FUNÇÃO PARA ENVIAR MENSAGENS
function sendMessage() {
    const message = messageInput.value.trim();
    if (message && ws.readyState === WebSocket.OPEN) {
        // Envia a mensagem para o servidor. 
        // O servidor irá fazer o broadcast incluindo nosso nome de usuário.
        ws.send(message);
        
        // Limpa o input
        messageInput.value = "";
        messageInput.focus();
    }
}

// 5. LISTENERS DE EVENTOS
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keyup", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});