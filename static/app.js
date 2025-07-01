console.log("app.js foi carregado e está executando!");

const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");

// Verifica se a variável do usuário existe
if (typeof authenticated_user === 'undefined') {
    console.error("ERRO: A variável 'authenticated_user' não foi definida no HTML.");
}

const socketProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const socketUrl = `${socketProtocol}//${window.location.host}/chat`;

console.log(`Tentando conectar ao WebSocket em: ${socketUrl}`); // Ponto de verificação 2

const ws = new WebSocket(socketUrl);

ws.onopen = function () {
    console.log("SUCESSO: Conexão WebSocket aberta!"); // Ponto de verificação 3
    if (authenticated_user) {
        ws.send(authenticated_user);
    }
};

ws.onclose = function (event) {
    console.error("FALHA: Conexão WebSocket foi fechada.", event); // Ponto de verificação 4
    messagesDiv.textContent += "\n--- Conexão com o servidor perdida. Por favor, atualize a página. ---\n";
};

ws.onerror = function (error) {
    console.error("ERRO: Ocorreu um erro no WebSocket.", error); // Ponto de verificação 5
};


// O resto das funções (onmessage, sendMessage, etc.) continua igual...
ws.onmessage = function (event) {
    const message = event.data;
    if (messagesDiv.textContent.length > 0) {
        messagesDiv.textContent += "\n" + message;
    } else {
        messagesDiv.textContent = message;
    }
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

function sendMessage() {
    const message = messageInput.value.trim();
    if (message && ws.readyState === WebSocket.OPEN) {
        ws.send(message);
        messageInput.value = "";
        messageInput.focus();
    }
}

sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keyup", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});