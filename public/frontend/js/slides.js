/**
 * Slides Module - GapSense Demo
 * Slide navigation, dots, fullscreen controls
 */

import { TOTAL_SLIDES } from './constants.js';
import { currentSlide, setCurrentSlide } from './state.js';

/**
 * Initialize slide dots for both main and fullscreen views
 */
export function initSlideDots() {
  const dotsContainer = document.getElementById('slideDots');
  const fullscreenDotsContainer = document.getElementById('fullscreenSlideDots');

  for (let i = 0; i < TOTAL_SLIDES; i++) {
    // Main dots
    const dot = document.createElement('div');
    dot.className = 'dot' + (i === 0 ? ' active' : '');
    dot.onclick = () => goToSlide(i);
    dotsContainer.appendChild(dot);

    // Fullscreen dots
    const fsDot = document.createElement('div');
    fsDot.className = 'dot' + (i === 0 ? ' active' : '');
    fsDot.onclick = () => goToSlide(i);
    fullscreenDotsContainer.appendChild(fsDot);
  }
}

/**
 * Change slide by direction (-1 for prev, +1 for next)
 * @param {number} direction - -1 or 1
 */
export function changeSlide(direction) {
  let newSlide = currentSlide + direction;

  // Wrap around
  if (newSlide < 0) newSlide = TOTAL_SLIDES - 1;
  if (newSlide >= TOTAL_SLIDES) newSlide = 0;

  setCurrentSlide(newSlide);
  updateSlides();
}

/**
 * Go to specific slide by index
 * @param {number} index - Slide index (0-based)
 */
export function goToSlide(index) {
  setCurrentSlide(index);
  updateSlides();
}

/**
 * Update slide positions and UI indicators
 */
export function updateSlides() {
  const track = document.getElementById('slidesTrack');
  const fsTrack = document.getElementById('fullscreenSlidesTrack');
  const offset = -currentSlide * 100;

  // Update track positions with hardware acceleration
  track.style.transform = `translateX(${offset}%)`;
  fsTrack.style.transform = `translateX(${offset}%)`;

  // Update dots
  document.querySelectorAll('.dot').forEach((dot, index) => {
    dot.classList.toggle('active', index === currentSlide);
  });

  // Update counters
  const counterText = `${currentSlide + 1}/${TOTAL_SLIDES}`;
  document.getElementById('slideCounter').textContent = counterText;
  document.getElementById('fullscreenSlideCounter').textContent = counterText;
}

/**
 * Open fullscreen slide view
 */
export function openFullscreen() {
  document.getElementById('fullscreenModal').classList.add('show');
}

/**
 * Close fullscreen slide view
 */
export function closeFullscreen() {
  document.getElementById('fullscreenModal').classList.remove('show');
}

// Expose functions to global scope for onclick handlers
// TODO: Replace with event delegation in future refactor
window.changeSlide = changeSlide;
window.goToSlide = goToSlide;
window.openFullscreen = openFullscreen;
window.closeFullscreen = closeFullscreen;
