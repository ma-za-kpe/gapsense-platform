/**
 * Toast Component - Mobile-Optimized
 * Lightweight notification system for small screens
 */

/**
 * @typedef {Object} ToastOptions
 * @property {'success'|'error'|'warning'|'info'} type - Toast type
 * @property {number} duration - Auto-dismiss duration in ms (0 = no auto-dismiss)
 * @property {'top'|'bottom'} position - Screen position
 * @property {boolean} dismissible - Allow manual dismiss
 * @property {string} icon - Custom icon (optional)
 */

export class Toast {
  /**
   * Create a toast notification
   * @param {string} message - Toast message
   * @param {ToastOptions} options - Toast configuration
   */
  constructor(message, options = {}) {
    this.message = message;
    this.options = {
      type: options.type || 'info',
      duration: options.duration !== undefined ? options.duration : 4000,
      position: options.position || 'bottom',
      dismissible: options.dismissible !== false,
      icon: options.icon || null
    };

    this.element = null;
    this.dismissTimeout = null;
  }

  /**
   * Show the toast
   */
  show() {
    this.element = this._createToast();
    const container = this._getContainer();
    container.appendChild(this.element);

    // Force reflow for animation
    this.element.offsetHeight;
    this.element.classList.add('toast--visible');

    // Auto-dismiss if duration > 0
    if (this.options.duration > 0) {
      this.dismissTimeout = setTimeout(() => {
        this.hide();
      }, this.options.duration);
    }

    return this;
  }

  /**
   * Hide the toast
   */
  hide() {
    if (!this.element) return;

    // Clear auto-dismiss timeout
    if (this.dismissTimeout) {
      clearTimeout(this.dismissTimeout);
      this.dismissTimeout = null;
    }

    this.element.classList.remove('toast--visible');
    this.element.classList.add('toast--hiding');

    // Wait for fade-out animation
    setTimeout(() => {
      if (this.element && this.element.parentNode) {
        this.element.parentNode.removeChild(this.element);
      }
      this.element = null;
    }, 300); // Match CSS transition duration
  }

  /**
   * Get or create toast container
   * @private
   * @returns {HTMLElement}
   */
  _getContainer() {
    const containerId = `toast-container-${this.options.position}`;
    let container = document.getElementById(containerId);

    if (!container) {
      container = document.createElement('div');
      container.id = containerId;
      container.className = `toast-container toast-container--${this.options.position}`;
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'false');
      document.body.appendChild(container);
    }

    return container;
  }

  /**
   * Create toast DOM element
   * @private
   * @returns {HTMLElement}
   */
  _createToast() {
    const toast = document.createElement('div');
    toast.className = `toast toast--${this.options.type}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');

    // Icon
    const icon = document.createElement('div');
    icon.className = 'toast__icon';
    icon.innerHTML = this._getIcon();
    toast.appendChild(icon);

    // Message
    const messageEl = document.createElement('div');
    messageEl.className = 'toast__message';
    messageEl.textContent = this.message;
    toast.appendChild(messageEl);

    // Dismiss button (if dismissible)
    if (this.options.dismissible) {
      const dismissBtn = document.createElement('button');
      dismissBtn.className = 'toast__dismiss';
      dismissBtn.setAttribute('aria-label', 'Dismiss notification');
      dismissBtn.innerHTML = '&times;';
      dismissBtn.addEventListener('click', () => this.hide());
      toast.appendChild(dismissBtn);

      // Touch-to-dismiss (swipe)
      this._addSwipeToDismiss(toast);
    }

    return toast;
  }

  /**
   * Get icon for toast type
   * @private
   * @returns {string}
   */
  _getIcon() {
    if (this.options.icon) {
      return this.options.icon;
    }

    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };

    return icons[this.options.type] || icons.info;
  }

  /**
   * Add swipe-to-dismiss gesture
   * @private
   * @param {HTMLElement} element
   */
  _addSwipeToDismiss(element) {
    let startX = 0;
    let startY = 0;
    let currentX = 0;

    const handleTouchStart = (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      element.style.transition = 'none';
    };

    const handleTouchMove = (e) => {
      currentX = e.touches[0].clientX - startX;
      const currentY = e.touches[0].clientY - startY;

      // Only track horizontal swipes (ignore vertical scrolling)
      if (Math.abs(currentX) > Math.abs(currentY)) {
        e.preventDefault();
        element.style.transform = `translateX(${currentX}px)`;
        element.style.opacity = Math.max(0.3, 1 - Math.abs(currentX) / 200);
      }
    };

    const handleTouchEnd = () => {
      element.style.transition = '';

      // Dismiss if swiped > 100px
      if (Math.abs(currentX) > 100) {
        this.hide();
      } else {
        // Reset position
        element.style.transform = '';
        element.style.opacity = '';
      }

      currentX = 0;
    };

    element.addEventListener('touchstart', handleTouchStart, { passive: true });
    element.addEventListener('touchmove', handleTouchMove, { passive: false });
    element.addEventListener('touchend', handleTouchEnd);
  }
}

/**
 * Toast manager for controlling multiple toasts
 */
class ToastManager {
  constructor() {
    this.toasts = [];
    this.maxToasts = 3; // Max simultaneous toasts
  }

  /**
   * Show a toast
   * @param {string} message
   * @param {ToastOptions} options
   * @returns {Toast}
   */
  show(message, options = {}) {
    // Remove oldest toast if at max capacity
    if (this.toasts.length >= this.maxToasts) {
      const oldestToast = this.toasts.shift();
      oldestToast.hide();
    }

    const toast = new Toast(message, options);
    this.toasts.push(toast);

    // Remove from tracking when hidden
    const originalHide = toast.hide.bind(toast);
    toast.hide = () => {
      originalHide();
      const index = this.toasts.indexOf(toast);
      if (index > -1) {
        this.toasts.splice(index, 1);
      }
    };

    toast.show();
    return toast;
  }

  /**
   * Show success toast
   * @param {string} message
   * @param {ToastOptions} options
   * @returns {Toast}
   */
  success(message, options = {}) {
    return this.show(message, { ...options, type: 'success' });
  }

  /**
   * Show error toast
   * @param {string} message
   * @param {ToastOptions} options
   * @returns {Toast}
   */
  error(message, options = {}) {
    return this.show(message, { ...options, type: 'error', duration: 6000 });
  }

  /**
   * Show warning toast
   * @param {string} message
   * @param {ToastOptions} options
   * @returns {Toast}
   */
  warning(message, options = {}) {
    return this.show(message, { ...options, type: 'warning', duration: 5000 });
  }

  /**
   * Show info toast
   * @param {string} message
   * @param {ToastOptions} options
   * @returns {Toast}
   */
  info(message, options = {}) {
    return this.show(message, { ...options, type: 'info' });
  }

  /**
   * Clear all toasts
   */
  clearAll() {
    this.toasts.forEach(toast => toast.hide());
    this.toasts = [];
  }
}

// Global toast manager instance (singleton)
const toastManager = new ToastManager();

// Export convenience functions
export function showToast(message, options) {
  return toastManager.show(message, options);
}

export function successToast(message, options) {
  return toastManager.success(message, options);
}

export function errorToast(message, options) {
  return toastManager.error(message, options);
}

export function warningToast(message, options) {
  return toastManager.warning(message, options);
}

export function infoToast(message, options) {
  return toastManager.info(message, options);
}

export function clearAllToasts() {
  toastManager.clearAll();
}

// Export for use in other modules
export default Toast;
