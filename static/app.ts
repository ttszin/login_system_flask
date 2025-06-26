// static/app.ts (VERSÃO FINAL CORRIGIDA)

// 1. SELECIONANDO OS ELEMENTOS DO "PALCO" (HTML)
const messagesDiv = document.getElementById("messages") as HTMLPreElement;
const messageInput = document.getElementById("message-input") as HTMLInputElement;
const sendButton = document.getElementById("send-button") as HTMLButtonElement;

// A variável 'authenticated_user' vem do template index.html
declare const authenticated_user: string;

const ws: WebSocket = new WebSocket("ws://localhost:8765");

ws.onopen = (): void => {
    console.log("Conectado à Ponte WebSocket!");
    if (authenticated_user) {
        ws.send(authenticated_user); 
    }
};

ws.onmessage = (event: MessageEvent): void => {
    // Esta função agora só cuida de mensagens recebidas de OUTROS usuários
    const message: string = event.data;
    messagesDiv.textContent += message;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

ws.onclose = (): void => {
    messagesDiv.textContent += "\n--- Conexão com o servidor perdida. Por favor, atualize a página. ---\n";
};

ws.onerror = (): void => {
    messagesDiv.textContent += "\n--- Ocorreu um erro na conexão. ---\n";
};


// ######################################################################
// A LÓGICA CORRIGIDA PARA ENVIAR MENSAGENS ESTÁ AQUI
// ######################################################################
function sendMessage(): void {
    const message: string = messageInput.value.trim();
    if (message && ws.readyState === WebSocket.OPEN) {
        
        // --- PASSO 1: ATUALIZA A PRÓPRIA TELA (A PARTE QUE FALTAVA) ---
        // Para consistência, formatamos a mensagem que aparece na nossa tela.
        const formattedMessage = `Você: ${message}\n`;
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
messageInput.addEventListener("keyup", (event: KeyboardEvent): void => {
    if (event.key === "Enter") {
        sendMessage();
    }
});