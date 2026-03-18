/**
 * Main Entry Point - GapSense Demo
 * Initialize all modules and set up event listeners
 * Mobile-first, ES6 modular architecture
 */

import { initSlideDots } from './slides.js';
import { initTouchListeners, initKeyboardNavigation } from './mobile.js';
import { initDemo, handleKeyDown } from './api.js';

/**
 * Register Service Worker for offline support
 */
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('✅ Service Worker registered:', registration.scope);

      // Listen for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('🔄 New version available. Refresh to update.');
          }
        });
      });
    } catch (error) {
      console.warn('⚠️ Service Worker registration failed:', error);
    }
  }
}

/**
 * Initialize all event listeners
 */
function initEventListeners() {
  // Auto-resize textarea as user types
  const messageInput = document.getElementById('messageInput');
  if (messageInput) {
    messageInput.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = this.scrollHeight + 'px';
    });

    // Handle Enter key to send message
    messageInput.addEventListener('keydown', handleKeyDown);
  }

  // Touch listeners for swipe gestures
  initTouchListeners();

  // Keyboard navigation (Arrow keys, Escape)
  initKeyboardNavigation();
}

/**
 * Main initialization function
 */
async function init() {
  try {
    // Initialize slide navigation
    initSlideDots();

    // Initialize event listeners
    initEventListeners();

    // Register service worker for offline support
    registerServiceWorker();

    // Load teacher info
    await initDemo();

    console.log('✅ GapSense Demo initialized - Mobile-first ES6 modules + PWA');
  } catch (error) {
    console.error('❌ Error initializing demo:', error);
  }
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
