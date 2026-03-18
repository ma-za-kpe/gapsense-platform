/**
 * LoadingSpinner Component - Mobile-Optimized
 * Hardware-accelerated animations for smooth 60fps on mobile
 */

/**
 * @typedef {Object} SpinnerOptions
 * @property {'spinner'|'dots'|'pulse'} type - Animation type
 * @property {'small'|'medium'|'large'} size - Spinner size
 * @property {string} color - CSS color (default: var(--color-primary))
 * @property {string} message - Optional loading message
 * @property {boolean} overlay - Show fullscreen overlay (default: false)
 */

export class LoadingSpinner {
  /**
   * Create a loading spinner
   * @param {SpinnerOptions} options - Spinner configuration
   */
  constructor(options = {}) {
    this.options = {
      type: options.type || 'spinner',
      size: options.size || 'medium',
      color: options.color || 'var(--color-primary)',
      message: options.message || '',
      overlay: options.overlay || false
    };

    this.element = null;
    this.isVisible = false;
  }

  /**
   * Show the loading spinner
   * @param {string} message - Optional message to display
   */
  show(message) {
    if (this.isVisible) return;

    if (message) {
      this.options.message = message;
    }

    this.element = this._createSpinner();
    document.body.appendChild(this.element);
    this.isVisible = true;

    // Force reflow for animation
    this.element.offsetHeight;
    this.element.classList.add('loading-spinner--visible');
  }

  /**
   * Hide the loading spinner
   */
  hide() {
    if (!this.isVisible || !this.element) return;

    this.element.classList.remove('loading-spinner--visible');

    // Wait for fade-out animation
    setTimeout(() => {
      if (this.element && this.element.parentNode) {
        this.element.parentNode.removeChild(this.element);
      }
      this.element = null;
      this.isVisible = false;
    }, 200); // Match CSS transition duration
  }

  /**
   * Update loading message
   * @param {string} message - New message
   */
  updateMessage(message) {
    if (!this.element) return;

    const messageEl = this.element.querySelector('.loading-spinner__message');
    if (messageEl) {
      messageEl.textContent = message;
    }
  }

  /**
   * Create spinner DOM element
   * @private
   * @returns {HTMLElement}
   */
  _createSpinner() {
    const container = document.createElement('div');
    container.className = `loading-spinner loading-spinner--${this.options.size}`;

    if (this.options.overlay) {
      container.classList.add('loading-spinner--overlay');
    }

    // ARIA attributes for accessibility
    container.setAttribute('role', 'status');
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-busy', 'true');

    // Spinner content
    const content = document.createElement('div');
    content.className = 'loading-spinner__content';

    // Animation element
    const animation = this._createAnimation();
    content.appendChild(animation);

    // Message (if provided)
    if (this.options.message) {
      const message = document.createElement('div');
      message.className = 'loading-spinner__message';
      message.textContent = this.options.message;
      content.appendChild(message);
    }

    // Screen reader text
    const srText = document.createElement('span');
    srText.className = 'sr-only';
    srText.textContent = this.options.message || 'Loading...';
    content.appendChild(srText);

    container.appendChild(content);
    return container;
  }

  /**
   * Create animation element based on type
   * @private
   * @returns {HTMLElement}
   */
  _createAnimation() {
    const wrapper = document.createElement('div');
    wrapper.className = `loading-spinner__animation loading-spinner__animation--${this.options.type}`;
    wrapper.style.setProperty('--spinner-color', this.options.color);

    switch (this.options.type) {
      case 'dots':
        return this._createDotsAnimation(wrapper);
      case 'pulse':
        return this._createPulseAnimation(wrapper);
      case 'spinner':
      default:
        return this._createSpinnerAnimation(wrapper);
    }
  }

  /**
   * Create rotating spinner animation
   * @private
   */
  _createSpinnerAnimation(wrapper) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner__spinner';

    // Create 8 spinner bars for smooth rotation
    for (let i = 0; i < 8; i++) {
      const bar = document.createElement('div');
      bar.className = 'loading-spinner__spinner-bar';
      bar.style.transform = `rotate(${i * 45}deg) translate(0, -150%)`;
      bar.style.animationDelay = `${i * 0.1}s`;
      spinner.appendChild(bar);
    }

    wrapper.appendChild(spinner);
    return wrapper;
  }

  /**
   * Create bouncing dots animation
   * @private
   */
  _createDotsAnimation(wrapper) {
    const dots = document.createElement('div');
    dots.className = 'loading-spinner__dots';

    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'loading-spinner__dot';
      dot.style.animationDelay = `${i * 0.15}s`;
      dots.appendChild(dot);
    }

    wrapper.appendChild(dots);
    return wrapper;
  }

  /**
   * Create pulsing animation
   * @private
   */
  _createPulseAnimation(wrapper) {
    const pulse = document.createElement('div');
    pulse.className = 'loading-spinner__pulse';

    // Create 3 concentric rings
    for (let i = 0; i < 3; i++) {
      const ring = document.createElement('div');
      ring.className = 'loading-spinner__pulse-ring';
      ring.style.animationDelay = `${i * 0.4}s`;
      pulse.appendChild(ring);
    }

    wrapper.appendChild(pulse);
    return wrapper;
  }
}

/**
 * Global loading spinner instance (singleton)
 */
let globalSpinner = null;

/**
 * Show global loading spinner
 * @param {string} message - Loading message
 * @param {SpinnerOptions} options - Spinner options
 */
export function showLoading(message, options = {}) {
  if (!globalSpinner) {
    globalSpinner = new LoadingSpinner({ ...options, overlay: true });
  }
  globalSpinner.show(message);
}

/**
 * Hide global loading spinner
 */
export function hideLoading() {
  if (globalSpinner) {
    globalSpinner.hide();
  }
}

/**
 * Update global loading message
 * @param {string} message - New message
 */
export function updateLoadingMessage(message) {
  if (globalSpinner) {
    globalSpinner.updateMessage(message);
  }
}

// Export for use in other modules
export default LoadingSpinner;
