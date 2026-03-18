/**
 * TouchHandler - Mobile-Optimized Touch and Swipe Gestures
 * Handles touch events, swipe gestures, and touch-friendly interactions
 */

/**
 * @typedef {Object} TouchOptions
 * @property {number} swipeThreshold - Minimum distance for swipe (px)
 * @property {number} tapTimeout - Maximum duration for tap (ms)
 * @property {boolean} preventDefault - Prevent default touch behavior
 * @property {Function} onSwipeLeft - Callback for swipe left
 * @property {Function} onSwipeRight - Callback for swipe right
 * @property {Function} onSwipeUp - Callback for swipe up
 * @property {Function} onSwipeDown - Callback for swipe down
 * @property {Function} onTap - Callback for tap
 * @property {Function} onLongPress - Callback for long press
 * @property {Function} onPinch - Callback for pinch (zoom)
 */

export class TouchHandler {
  /**
   * Create a touch handler
   * @param {HTMLElement} element - Element to attach touch events
   * @param {TouchOptions} options - Touch configuration
   */
  constructor(element, options = {}) {
    if (!element) {
      throw new Error('TouchHandler requires an element');
    }

    this.element = element;
    this.options = {
      swipeThreshold: options.swipeThreshold || 50,
      tapTimeout: options.tapTimeout || 300,
      longPressTimeout: options.longPressTimeout || 500,
      preventDefault: options.preventDefault !== false,
      onSwipeLeft: options.onSwipeLeft || null,
      onSwipeRight: options.onSwipeRight || null,
      onSwipeUp: options.onSwipeUp || null,
      onSwipeDown: options.onSwipeDown || null,
      onTap: options.onTap || null,
      onLongPress: options.onLongPress || null,
      onPinch: options.onPinch || null
    };

    // Touch state
    this.touchStartX = 0;
    this.touchStartY = 0;
    this.touchStartTime = 0;
    this.touchDistance = 0;
    this.isSwiping = false;
    this.longPressTimer = null;
    this.initialPinchDistance = 0;

    // Bind methods
    this.handleTouchStart = this.handleTouchStart.bind(this);
    this.handleTouchMove = this.handleTouchMove.bind(this);
    this.handleTouchEnd = this.handleTouchEnd.bind(this);

    // Initialize
    this.attach();
  }

  /**
   * Attach touch event listeners
   */
  attach() {
    this.element.addEventListener('touchstart', this.handleTouchStart, { passive: !this.options.preventDefault });
    this.element.addEventListener('touchmove', this.handleTouchMove, { passive: !this.options.preventDefault });
    this.element.addEventListener('touchend', this.handleTouchEnd);
    this.element.addEventListener('touchcancel', this.handleTouchEnd);
  }

  /**
   * Remove touch event listeners
   */
  detach() {
    this.element.removeEventListener('touchstart', this.handleTouchStart);
    this.element.removeEventListener('touchmove', this.handleTouchMove);
    this.element.removeEventListener('touchend', this.handleTouchEnd);
    this.element.removeEventListener('touchcancel', this.handleTouchEnd);
    this._clearLongPressTimer();
  }

  /**
   * Handle touch start
   * @private
   */
  handleTouchStart(e) {
    if (this.options.preventDefault) {
      e.preventDefault();
    }

    const touch = e.touches[0];
    this.touchStartX = touch.clientX;
    this.touchStartY = touch.clientY;
    this.touchStartTime = Date.now();
    this.isSwiping = false;

    // Handle multi-touch (pinch)
    if (e.touches.length === 2 && this.options.onPinch) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      this.initialPinchDistance = this._getDistance(touch1, touch2);
    }

    // Setup long press detection
    if (this.options.onLongPress) {
      this._setupLongPress(e);
    }
  }

  /**
   * Handle touch move
   * @private
   */
  handleTouchMove(e) {
    // Handle pinch gesture
    if (e.touches.length === 2 && this.options.onPinch) {
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const currentDistance = this._getDistance(touch1, touch2);
      const scale = currentDistance / this.initialPinchDistance;

      this.options.onPinch({
        scale,
        originalEvent: e
      });

      if (this.options.preventDefault) {
        e.preventDefault();
      }
      return;
    }

    // Handle swipe gesture
    const touch = e.touches[0];
    const deltaX = touch.clientX - this.touchStartX;
    const deltaY = touch.clientY - this.touchStartY;
    const distance = Math.sqrt(deltaX ** 2 + deltaY ** 2);

    // Cancel long press if moved
    if (distance > 10) {
      this._clearLongPressTimer();
    }

    // Detect if this is a swipe (horizontal or vertical)
    if (!this.isSwiping && distance > this.options.swipeThreshold) {
      this.isSwiping = true;
      this.touchDistance = distance;

      // Determine swipe direction
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        // Horizontal swipe
        if (this.options.preventDefault) {
          e.preventDefault();
        }
      }
    }
  }

  /**
   * Handle touch end
   * @private
   */
  handleTouchEnd(e) {
    this._clearLongPressTimer();

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - this.touchStartX;
    const deltaY = touch.clientY - this.touchStartY;
    const duration = Date.now() - this.touchStartTime;
    const distance = Math.sqrt(deltaX ** 2 + deltaY ** 2);

    // Determine gesture type
    if (this.isSwiping || distance > this.options.swipeThreshold) {
      // Swipe gesture
      this._handleSwipe(deltaX, deltaY, distance, duration);
    } else if (duration < this.options.tapTimeout) {
      // Tap gesture
      if (this.options.onTap) {
        this.options.onTap({
          x: touch.clientX,
          y: touch.clientY,
          originalEvent: e
        });
      }
    }

    // Reset state
    this.isSwiping = false;
    this.touchDistance = 0;
    this.initialPinchDistance = 0;
  }

  /**
   * Handle swipe gesture
   * @private
   */
  _handleSwipe(deltaX, deltaY, distance, duration) {
    const velocity = distance / duration;

    // Determine primary direction
    const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY);

    if (isHorizontal) {
      // Horizontal swipe
      if (deltaX > 0 && this.options.onSwipeRight) {
        this.options.onSwipeRight({
          distance,
          velocity,
          duration
        });
      } else if (deltaX < 0 && this.options.onSwipeLeft) {
        this.options.onSwipeLeft({
          distance,
          velocity,
          duration
        });
      }
    } else {
      // Vertical swipe
      if (deltaY > 0 && this.options.onSwipeDown) {
        this.options.onSwipeDown({
          distance,
          velocity,
          duration
        });
      } else if (deltaY < 0 && this.options.onSwipeUp) {
        this.options.onSwipeUp({
          distance,
          velocity,
          duration
        });
      }
    }
  }

  /**
   * Setup long press detection
   * @private
   */
  _setupLongPress(e) {
    this.longPressTimer = setTimeout(() => {
      const touch = e.touches[0];
      this.options.onLongPress({
        x: touch.clientX,
        y: touch.clientY,
        originalEvent: e
      });
    }, this.options.longPressTimeout);
  }

  /**
   * Clear long press timer
   * @private
   */
  _clearLongPressTimer() {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
  }

  /**
   * Get distance between two touch points
   * @private
   */
  _getDistance(touch1, touch2) {
    const deltaX = touch2.clientX - touch1.clientX;
    const deltaY = touch2.clientY - touch1.clientY;
    return Math.sqrt(deltaX ** 2 + deltaY ** 2);
  }

  /**
   * Destroy touch handler
   */
  destroy() {
    this.detach();
    this.element = null;
  }
}

/**
 * SwipeableCard - Utility for swipeable student/report cards
 */
export class SwipeableCard {
  constructor(element, options = {}) {
    this.element = element;
    this.options = {
      threshold: options.threshold || 100,
      onSwipeLeft: options.onSwipeLeft || null,
      onSwipeRight: options.onSwipeRight || null,
      animationDuration: options.animationDuration || 300
    };

    this.startX = 0;
    this.currentX = 0;
    this.isDragging = false;

    this._init();
  }

  _init() {
    this.element.style.transition = 'none';
    this.element.style.cursor = 'grab';

    this.touchHandler = new TouchHandler(this.element, {
      preventDefault: false,
      onTap: () => {
        // Allow default tap behavior
      },
      onSwipeLeft: (e) => {
        this._handleSwipeComplete('left', e);
      },
      onSwipeRight: (e) => {
        this._handleSwipeComplete('right', e);
      }
    });

    // Add visual feedback during drag
    this.element.addEventListener('touchstart', this._handleDragStart.bind(this));
    this.element.addEventListener('touchmove', this._handleDragMove.bind(this));
    this.element.addEventListener('touchend', this._handleDragEnd.bind(this));
  }

  _handleDragStart(e) {
    this.isDragging = true;
    this.startX = e.touches[0].clientX;
    this.element.style.transition = 'none';
    this.element.style.cursor = 'grabbing';
  }

  _handleDragMove(e) {
    if (!this.isDragging) return;

    this.currentX = e.touches[0].clientX - this.startX;

    // Apply visual feedback
    const opacity = 1 - Math.abs(this.currentX) / 300;
    this.element.style.transform = `translateX(${this.currentX}px)`;
    this.element.style.opacity = Math.max(0.3, opacity);
  }

  _handleDragEnd() {
    if (!this.isDragging) return;
    this.isDragging = false;

    // Reset or complete swipe based on threshold
    if (Math.abs(this.currentX) < this.options.threshold) {
      // Reset position
      this.element.style.transition = `all ${this.options.animationDuration}ms ease`;
      this.element.style.transform = 'translateX(0)';
      this.element.style.opacity = '1';
      this.element.style.cursor = 'grab';
    }

    this.currentX = 0;
  }

  _handleSwipeComplete(direction, event) {
    // Animate card out
    const distance = direction === 'left' ? -400 : 400;
    this.element.style.transition = `all ${this.options.animationDuration}ms ease`;
    this.element.style.transform = `translateX(${distance}px)`;
    this.element.style.opacity = '0';

    // Callback after animation
    setTimeout(() => {
      if (direction === 'left' && this.options.onSwipeLeft) {
        this.options.onSwipeLeft(event);
      } else if (direction === 'right' && this.options.onSwipeRight) {
        this.options.onSwipeRight(event);
      }

      // Reset card
      this.reset();
    }, this.options.animationDuration);
  }

  reset() {
    this.element.style.transition = 'none';
    this.element.style.transform = 'translateX(0)';
    this.element.style.opacity = '1';
    this.element.style.cursor = 'grab';
  }

  destroy() {
    if (this.touchHandler) {
      this.touchHandler.destroy();
    }
    this.element.removeEventListener('touchstart', this._handleDragStart);
    this.element.removeEventListener('touchmove', this._handleDragMove);
    this.element.removeEventListener('touchend', this._handleDragEnd);
  }
}

/**
 * PullToRefresh - Utility for pull-to-refresh interaction
 */
export class PullToRefresh {
  constructor(element, options = {}) {
    this.element = element;
    this.options = {
      threshold: options.threshold || 80,
      onRefresh: options.onRefresh || null,
      refreshingText: options.refreshingText || 'Refreshing...',
      pullText: options.pullText || 'Pull to refresh'
    };

    this.startY = 0;
    this.currentY = 0;
    this.isPulling = false;
    this.isRefreshing = false;

    this._init();
  }

  _init() {
    // Create refresh indicator
    this.indicator = document.createElement('div');
    this.indicator.className = 'pull-to-refresh-indicator';
    this.indicator.textContent = this.options.pullText;
    this.indicator.style.cssText = `
      position: absolute;
      top: -60px;
      left: 0;
      right: 0;
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #666;
      font-size: 14px;
      transition: transform 300ms ease;
    `;
    this.element.parentElement.style.position = 'relative';
    this.element.parentElement.insertBefore(this.indicator, this.element);

    // Attach touch events
    this.element.addEventListener('touchstart', this._handleTouchStart.bind(this), { passive: true });
    this.element.addEventListener('touchmove', this._handleTouchMove.bind(this));
    this.element.addEventListener('touchend', this._handleTouchEnd.bind(this));
  }

  _handleTouchStart(e) {
    if (this.isRefreshing) return;

    // Only trigger if scrolled to top
    if (this.element.scrollTop === 0) {
      this.startY = e.touches[0].clientY;
      this.isPulling = true;
    }
  }

  _handleTouchMove(e) {
    if (!this.isPulling || this.isRefreshing) return;

    this.currentY = e.touches[0].clientY - this.startY;

    if (this.currentY > 0) {
      e.preventDefault();

      // Visual feedback
      const pullDistance = Math.min(this.currentY, this.options.threshold * 1.5);
      const opacity = Math.min(pullDistance / this.options.threshold, 1);

      this.indicator.style.transform = `translateY(${pullDistance}px)`;
      this.indicator.style.opacity = opacity;

      if (this.currentY >= this.options.threshold) {
        this.indicator.textContent = 'Release to refresh';
      } else {
        this.indicator.textContent = this.options.pullText;
      }
    }
  }

  _handleTouchEnd() {
    if (!this.isPulling || this.isRefreshing) return;

    if (this.currentY >= this.options.threshold) {
      // Trigger refresh
      this._startRefresh();
    } else {
      // Reset
      this._reset();
    }

    this.isPulling = false;
    this.currentY = 0;
  }

  async _startRefresh() {
    this.isRefreshing = true;
    this.indicator.textContent = this.options.refreshingText;
    this.indicator.style.transform = `translateY(${this.options.threshold}px)`;

    if (this.options.onRefresh) {
      await this.options.onRefresh();
    }

    this._reset();
    this.isRefreshing = false;
  }

  _reset() {
    this.indicator.style.transition = 'all 300ms ease';
    this.indicator.style.transform = 'translateY(0)';
    this.indicator.style.opacity = '0';

    setTimeout(() => {
      this.indicator.style.transition = '';
      this.indicator.textContent = this.options.pullText;
    }, 300);
  }

  destroy() {
    if (this.indicator && this.indicator.parentElement) {
      this.indicator.parentElement.removeChild(this.indicator);
    }
    this.element.removeEventListener('touchstart', this._handleTouchStart);
    this.element.removeEventListener('touchmove', this._handleTouchMove);
    this.element.removeEventListener('touchend', this._handleTouchEnd);
  }
}

/**
 * Utility: Add ripple effect on touch
 */
export function addRippleEffect(element) {
  element.style.position = 'relative';
  element.style.overflow = 'hidden';

  element.addEventListener('touchstart', (e) => {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const x = e.touches[0].clientX - rect.left;
    const y = e.touches[0].clientY - rect.top;

    ripple.style.cssText = `
      position: absolute;
      left: ${x}px;
      top: ${y}px;
      width: 0;
      height: 0;
      border-radius: 50%;
      background: rgba(37, 211, 102, 0.4);
      transform: translate(-50%, -50%);
      animation: ripple 600ms ease-out;
      pointer-events: none;
    `;

    element.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  });

  // Add ripple animation keyframes
  if (!document.getElementById('ripple-animation')) {
    const style = document.createElement('style');
    style.id = 'ripple-animation';
    style.textContent = `
      @keyframes ripple {
        to {
          width: 200px;
          height: 200px;
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }
}

// Export for use in other modules
export default TouchHandler;
