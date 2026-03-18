/**
 * State Management - GapSense Demo
 * Centralized state for slides, touch gestures, and analysis polling
 */

// Slide state
export let currentSlide = 0;

export function setCurrentSlide(value) {
  currentSlide = value;
}

// Touch gesture state
export let touchStartX = 0;
export let touchEndX = 0;

export function setTouchStartX(value) {
  touchStartX = value;
}

export function setTouchEndX(value) {
  touchEndX = value;
}

// Analysis polling state
export let analysisPollingInterval = null;
export let initialAnalysisTimestamp = null;

export function setAnalysisPollingInterval(value) {
  analysisPollingInterval = value;
}

export function setInitialAnalysisTimestamp(value) {
  initialAnalysisTimestamp = value;
}

/**
 * Reset all state (useful for cleanup/testing)
 */
export function resetState() {
  currentSlide = 0;
  touchStartX = 0;
  touchEndX = 0;

  if (analysisPollingInterval) {
    clearInterval(analysisPollingInterval);
  }
  analysisPollingInterval = null;
  initialAnalysisTimestamp = null;
}
