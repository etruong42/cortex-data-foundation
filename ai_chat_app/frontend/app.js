const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const welcomeMessage = document.querySelector('.welcome-message');

let history = [];

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
}

function setInput(text) {
  userInput.value = text;
  autoResize(userInput);
  userInput.focus();
}

function appendMessage(role, text) {
  if (welcomeMessage) {
    welcomeMessage.style.display = 'none';
  }

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  // Avatar
  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.innerHTML = role === 'user'
    ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
    : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/><path d="M8 14h8"/><path d="M8 17h8"/></svg>';

  // Content
  const content = document.createElement('div');
  content.className = 'message-content prose';

  if (role === 'bot') {
    const cleanArgs = DOMPurify.sanitize(text);
    content.innerHTML = marked.parse(cleanArgs);
  } else {
    content.textContent = text;
  }

  messageDiv.appendChild(avatar);
  messageDiv.appendChild(content);
  chatContainer.appendChild(messageDiv);

  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendLoading() {
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message bot loading';
  loadingDiv.id = 'loading-indicator';
  loadingDiv.innerHTML = `
        <div class="avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/></svg>
        </div>
        <div class="message-content">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
  chatContainer.appendChild(loadingDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeLoading() {
  const loadingDiv = document.getElementById('loading-indicator');
  if (loadingDiv) {
    loadingDiv.remove();
  }
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = '';
  userInput.style.height = 'auto';
  sendBtn.disabled = true;

  appendMessage('user', text);
  appendLoading();

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: text,
        history: history
      })
    });

    const data = await response.json();
    removeLoading();

    if (data.events) {
      // Process events sequentially
      for (const event of data.events) {
        if (event.type === 'text') {
          appendMessage('bot', event.content);
        } else if (event.type === 'tool_call') {
          appendToolCall(event.tool_name, event.args);
        } else if (event.type === 'tool_result') {
          appendToolResult(event.tool_name, event.result);
        }
      }
    } else if (data.response) {
      // Fallback for old API if needed (though we updated it)
      appendMessage('bot', data.response);
    } else {
      appendMessage('bot', 'Sorry, I encountered an error potentially due to empty response.');
    }

  } catch (error) {
    removeLoading();
    console.error('Error:', error);
    appendMessage('bot', 'Sorry, I could not reach the server.');
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

function appendToolCall(name, args) {
  const div = document.createElement('div');
  div.className = 'tool-call';
  div.innerHTML = `
        <div class="tool-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
            <span>Using Tool: ${name}</span>
        </div>
        <div class="tool-args">${JSON.stringify(args, null, 2)}</div>
    `;

  // Check if last element is a bot message container, if so append to it? 
  // Actually, distinct bubbles for tools might be better or interspersed.
  // Let's create a "bot" message container if distinct, or just append to chatContainer directly for now to be simple.
  // But we usually want them inside the bot column.

  // Wrap in a bot message structure to align left
  const wrapper = document.createElement('div');
  wrapper.className = 'message bot';
  wrapper.style.marginBottom = '0.5rem'; // tighter spacing

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/></svg>';

  const content = document.createElement('div');
  // We don't use .message-content class here to avoid the background style, 
  // or we override it.
  content.style.flex = '1';
  content.appendChild(div);

  wrapper.appendChild(avatar);
  wrapper.appendChild(content);

  chatContainer.appendChild(wrapper);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendToolResult(name, result) {
  const div = document.createElement('div');
  div.className = 'tool-result';

  // Truncate result if too long for display?
  let displayResult = result;
  if (result.length > 500) {
    displayResult = result.substring(0, 500) + '... (truncated)';
  }

  div.innerHTML = `
        <div class="tool-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>Tool Result: ${name}</span>
        </div>
        <div class="tool-output">${displayResult}</div>
    `;

  const wrapper = document.createElement('div');
  wrapper.className = 'message bot';
  wrapper.style.marginBottom = '0.5rem';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.style.visibility = 'hidden'; // Hide avatar to align with previous

  const content = document.createElement('div');
  content.style.flex = '1';
  content.appendChild(div);

  wrapper.appendChild(avatar);
  wrapper.appendChild(content);

  chatContainer.appendChild(wrapper);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
