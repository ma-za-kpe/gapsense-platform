/**
 * UI Functions - GapSense Demo
 * WhatsApp message UI, typing indicators, and message parsing
 */

import { sendButtonClick } from './api.js';

/**
 * Add a message to the WhatsApp chat UI
 * @param {string} text - Message text (can include HTML)
 * @param {boolean} isSent - true for sent messages, false for received
 */
export function addMessage(text, isSent = false) {
  const messagesDiv = document.getElementById('messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${isSent ? 'sent' : 'received'}`;

  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const { messageText, buttons } = parseButtonsFromMessage(text);
  let bubbleContent = messageText.replace(/\n/g, '<br>');

  // Add interactive buttons for received messages
  if (buttons.length > 0 && !isSent) {
    bubbleContent += '<div class="button-container">';
    buttons.forEach(button => {
      bubbleContent += `
        <button class="whatsapp-button" onclick="window.sendButtonClick('${escapeHtml(button.text)}', '${button.id}')">
          ${escapeHtml(button.text)}
        </button>
      `;
    });
    bubbleContent += '</div>';
  }

  messageDiv.innerHTML = `
    <div>
      <div class="message-bubble">${bubbleContent}</div>
      <div class="message-time">${timeStr}</div>
    </div>
  `;

  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Parse buttons from message text
 * Buttons are lines starting with "• "
 * @param {string} text - Message text
 * @returns {{messageText: string, buttons: Array<{text: string, id: string}>}}
 */
export function parseButtonsFromMessage(text) {
  const lines = text.split('\n');
  const buttons = [];
  const messageLines = [];

  for (const line of lines) {
    if (line.trim().startsWith('• ')) {
      const buttonText = line.trim().substring(2);
      const buttonId = mapButtonTextToId(buttonText);
      buttons.push({ text: buttonText, id: buttonId });
    } else {
      messageLines.push(line);
    }
  }

  return { messageText: messageLines.join('\n').trim(), buttons };
}

/**
 * Map button text to a structured ID
 * @param {string} buttonText - Button text
 * @returns {string} Button ID
 */
function mapButtonTextToId(buttonText) {
  const lowerText = buttonText.toLowerCase();
  if (lowerText.includes('yes')) return 'confirm_yes';
  if (lowerText.includes('no')) return 'confirm_no';
  return buttonText.toLowerCase().replace(/[^a-z0-9]+/g, '_');
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Show typing indicator (3 animated dots)
 */
export function showTyping() {
  const messagesDiv = document.getElementById('messages');
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message received';
  typingDiv.id = 'typing-indicator';
  typingDiv.innerHTML = `
    <div>
      <div class="typing-indicator show">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  messagesDiv.appendChild(typingDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Hide typing indicator
 */
export function hideTyping() {
  const typingDiv = document.getElementById('typing-indicator');
  if (typingDiv) typingDiv.remove();
}

// Expose sendButtonClick to global scope for onclick handlers
// TODO: Replace with event delegation in future refactor
window.sendButtonClick = sendButtonClick;
