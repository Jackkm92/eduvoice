const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatWindow = document.getElementById('chat-window');

// Append a message to the chat window. sender can be 'user' or 'agent'.
function appendMessage(text, sender) {
    const msg = document.createElement('div');
    msg.classList.add('chat-message', sender);
    msg.textContent = text;
    chatWindow.appendChild(msg);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;
    appendMessage(message, 'user');
    userInput.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message }),
        });
        if (!response.ok) {
            throw new Error('Server error');
        }
        const data = await response.json();
        appendMessage(data.reply || data.response || JSON.stringify(data), 'agent');
    } catch (err) {
        appendMessage('Error: ' + err.message, 'agent');
    }
});