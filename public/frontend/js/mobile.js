/**
 * Mobile Touch Handlers - GapSense Demo
 * Swipe gestures and touch optimization for mobile devices
 */

import { POLLING } from './constants.js';
import { touchStartX, touchEndX, setTouchStartX, setTouchEndX } from './state.js';
import { changeSlide } from './slides.js';

/**
 * Handle touch start event
 * @param {TouchEvent} e - Touch event
 */
export function handleTouchStart(e) {
  setTouchStartX(e.changedTouches[0].screenX);
}

/**
 * Handle touch end event
 * @param {TouchEvent} e - Touch event
 */
export function handleTouchEnd(e) {
  setTouchEndX(e.changedTouches[0].screenX);
  handleSwipe();
}

/**
 * Process swipe gesture and trigger slide change if threshold met
 */
export function handleSwipe() {
  const swipeDistance = touchEndX - touchStartX;

  // Swipe left (next slide)
  if (swipeDistance < -POLLING.SWIPE_THRESHOLD) {
    changeSlide(1);
  }

  // Swipe right (previous slide)
  if (swipeDistance > POLLING.SWIPE_THRESHOLD) {
    changeSlide(-1);
  }
}

/**
 * Initialize touch event listeners for slide areas
 */
export function initTouchListeners() {
  document.querySelectorAll('.slides-area').forEach(area => {
    area.addEventListener('touchstart', handleTouchStart, { passive: true });
    area.addEventListener('touchend', handleTouchEnd, { passive: true });
  });
}

/**
 * Initialize keyboard navigation
 */
export function initKeyboardNavigation() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') changeSlide(-1);
    if (e.key === 'ArrowRight') changeSlide(1);

    // Close fullscreen on Escape
    if (e.key === 'Escape') {
      const fullscreenModal = document.getElementById('fullscreenModal');
      if (fullscreenModal && fullscreenModal.classList.contains('show')) {
        fullscreenModal.classList.remove('show');
      }
    }
  });
}
