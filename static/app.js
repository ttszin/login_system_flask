// static/app.ts (VERSÃO FINAL CORRIGIDA)
// 1. SELECIONANDO OS ELEMENTOS DO "PALCO" (HTML)
var messagesDiv = document.getElementById("messages");
var messageInput = document.getElementById("message-input");
var sendButton = document.getElementById("send-button");
var ws = new WebSocket(websocket_url); 
ws.onopen = function () {
    console.log("Conectado à Ponte WebSocket!");
    if (authenticated_user) {
        ws.send(authenticated_user);
    }
};
ws.onmessage = function (event) {
    // Esta função agora só cuida de mensagens recebidas de OUTROS usuários
    var message = event.data;
    messagesDiv.textContent += message;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};
ws.onclose = function () {
    messagesDiv.textContent += "\n--- Conexão com o servidor perdida. Por favor, atualize a página. ---\n";
};
ws.onerror = function () {
    messagesDiv.textContent += "\n--- Ocorreu um erro na conexão. ---\n";
};
// ######################################################################
// A LÓGICA CORRIGIDA PARA ENVIAR MENSAGENS ESTÁ AQUI
// ######################################################################
function sendMessage() {
    var message = messageInput.value.trim();
    if (message && ws.readyState === WebSocket.OPEN) {
        // --- PASSO 1: ATUALIZA A PRÓPRIA TELA (A PARTE QUE FALTAVA) ---
        // Para consistência, formatamos a mensagem que aparece na nossa tela.
        var formattedMessage = "Voc\u00EA: ".concat(message, "\n");
        messagesDiv.textContent += formattedMessage;
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Rola para baixo
        // --- PASSO 2: ENVIA A MENSAGEM "CRUA" PARA O SERVIDOR ---
        // O servidor receberá apenas a mensagem para fazer o broadcast com o nome de usuário correto.
        ws.send(message + "\n");
        // --- PASSO 3: LIMPA O INPUT ---
        messageInput.value = "";
        messageInput.focus();
    }
}
// ######################################################################
// Adicionando listeners de evento para o botão e a tecla Enter
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keyup", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});
