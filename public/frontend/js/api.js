/**
 * API Module - GapSense Demo
 * All API calls, image upload, polling, and teacher info
 */

import { API, FILE_LIMITS, TEACHER_PHONE, POLLING, ANALYSIS_STAGES, WAIT_MESSAGES } from './constants.js';
import { addMessage, showTyping, hideTyping } from './ui.js';
import {
  analysisPollingInterval,
  initialAnalysisTimestamp,
  setAnalysisPollingInterval,
  setInitialAnalysisTimestamp
} from './state.js';
import { apiClient, APIError } from './APIClient.js';

/**
 * Send a text message to the WhatsApp API
 */
export async function sendMessage() {
  const input = document.getElementById('messageInput');
  const message = input.value.trim();
  if (!message) return;

  addMessage(message, true);
  input.value = '';
  showTyping();

  try {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('teacher_phone', TEACHER_PHONE);

    const data = await apiClient.post(API.MESSAGE, formData);
    hideTyping();

    if (data.success && data.response) {
      addMessage(data.response);
      if (data.response.includes("Analyzing") && data.response.includes("exercise book")) {
        startPollingForCompletion();
      }
    } else {
      addMessage(`❌ Error: ${data.error}`);
    }
  } catch (error) {
    hideTyping();
    const errorMessage = error instanceof APIError
      ? error.getUserMessage()
      : `❌ Error: ${error.message}`;
    addMessage(errorMessage);
  }
}

/**
 * Send a quick predefined message
 * @param {string} message - Quick message text
 */
export async function sendQuickMessage(message) {
  document.getElementById('messageInput').value = message;
  await sendMessage();
}

/**
 * Handle button click in WhatsApp message
 * @param {string} buttonText - Button text to send
 * @param {string} buttonId - Button ID
 */
export async function sendButtonClick(buttonText, buttonId) {
  addMessage(buttonText, true);
  showTyping();

  try {
    const formData = new FormData();
    formData.append('message', buttonText);
    formData.append('button_id', buttonId);
    formData.append('teacher_phone', TEACHER_PHONE);

    const data = await apiClient.post(API.MESSAGE, formData);
    hideTyping();

    if (data.success && data.response) {
      addMessage(data.response);
      if (data.response.includes("Analyzing") && data.response.includes("exercise book")) {
        startPollingForCompletion();
      }
    } else {
      addMessage(`❌ Error: ${data.error}`);
    }
  } catch (error) {
    hideTyping();
    const errorMessage = error instanceof APIError
      ? error.getUserMessage()
      : `❌ Error: ${error.message}`;
    addMessage(errorMessage);
  }
}

/**
 * Handle image file selection and upload
 */
export async function handleImageSelect() {
  const input = document.getElementById('imageInput');
  const file = input.files[0];
  if (!file) return;

  // File size validation (5MB max) - Critical for 3G networks
  if (file.size > FILE_LIMITS.MAX_SIZE) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
    addMessage(`❌ Image too large (${sizeMB}MB). Maximum size is 5MB. Please try a smaller image or compress it.`, false);
    input.value = '';
    return;
  }

  addMessage(`📸 Uploading: ${file.name}`, true);
  showTyping();

  try {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('teacher_phone', TEACHER_PHONE);

    const data = await apiClient.post(API.UPLOAD_IMAGE, formData);
    hideTyping();

    if (data.success && data.response) {
      addMessage(data.response);
      if (data.response.includes("Analyzing")) {
        startPollingForCompletion();
      }
    } else {
      addMessage(`❌ Upload error: ${data.error}`);
    }
  } catch (error) {
    hideTyping();
    const errorMessage = error instanceof APIError
      ? error.getUserMessage()
      : `❌ Error: ${error.message}`;
    addMessage(errorMessage);
  }

  input.value = '';
}

/**
 * Check teacher info including last analysis timestamp
 * @returns {Promise<{success: boolean, students: Array, server_time: string}>}
 */
export async function checkTeacherInfo() {
  try {
    const data = await apiClient.get(`${API.TEACHER_INFO}?teacher_phone=${encodeURIComponent(TEACHER_PHONE)}`);
    return data;
  } catch (e) {
    console.error('Error checking teacher info:', e);
    return { success: false, students: [], server_time: new Date().toISOString() };
  }
}

/**
 * Get current analysis stage based on elapsed time
 * @param {number} elapsedSeconds - Seconds since analysis started
 * @returns {{step: number, time: number, progress: number, name: string, icon: string}}
 */
function getProgressStage(elapsedSeconds) {
  // Find the current stage based on elapsed time
  for (let i = ANALYSIS_STAGES.length - 1; i >= 0; i--) {
    if (elapsedSeconds >= ANALYSIS_STAGES[i].time) {
      return ANALYSIS_STAGES[i];
    }
  }
  return ANALYSIS_STAGES[0];
}

/**
 * Update progress UI in chat
 * @param {number} progress - Progress percentage (0-100)
 * @param {string} message - Stage message
 * @param {string} icon - Stage icon
 * @param {number} elapsed - Elapsed seconds
 * @param {string} [tip] - Optional educational tip
 */
function updateProgressUI(progress, message, icon, elapsed, tip = null) {
  // Find or create progress indicator
  let progressDiv = document.getElementById('analysis-progress');

  if (!progressDiv) {
    // Create progress indicator for first time
    const messagesDiv = document.getElementById('messages');
    progressDiv = document.createElement('div');
    progressDiv.className = 'message received';
    progressDiv.id = 'analysis-progress';
    messagesDiv.appendChild(progressDiv);
  }

  // Update content with progress bar
  const tipHtml = tip ? `<div style="font-size: 12px; color: #666; margin-top: 10px; padding: 8px; background: #F0F8FF; border-radius: 6px;">${tip}</div>` : '';

  progressDiv.innerHTML = `
    <div style="min-width: 200px;">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-size: 20px;">${icon}</span>
        <span style="font-weight: 500;">${message}</span>
      </div>
      <div style="background: #E0E0E0; height: 8px; border-radius: 10px; overflow: hidden; margin-bottom: 6px;">
        <div style="background: linear-gradient(90deg, #25D366 0%, #128C7E 100%); height: 100%; width: ${progress}%; transition: width 0.5s ease;"></div>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 11px; color: #666;">
        <span>${progress}%</span>
        <span>⏱️ ${elapsed}s</span>
      </div>
      ${tipHtml}
    </div>
  `;

  // Scroll to bottom
  const messagesDiv = document.getElementById('messages');
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/**
 * Remove progress indicator
 */
function removeProgressUI() {
  const progressDiv = document.getElementById('analysis-progress');
  if (progressDiv) {
    progressDiv.remove();
  }
}

/**
 * Check analysis status by parsing the reports page
 * @returns {Promise<{completed: boolean, gapCount: number, errorCount: number, hasIssues: boolean, timestamp: string|null}>}
 */
export async function checkAnalysisStatus() {
  try {
    const html = await apiClient.get(`${API.REPORTS}/${TEACHER_PHONE}`, { json: false });

    // Check 1: Gap tags count
    const gapMatches = html.match(/gap-tag/g);
    const gapCount = gapMatches ? gapMatches.length : 0;

    // Check 2: "Latest Analysis" section exists (indicates analysis completed)
    const hasLatestAnalysis = html.includes('Latest Analysis:');

    // Check 3: Error count in latest analysis
    const errorMatch = html.match(/❌ Errors Found \((\d+)\)/);
    const errorCount = errorMatch ? parseInt(errorMatch[1]) : 0;

    // Check 4: Extract timestamp from "Latest Analysis" section to detect new analysis
    const timestampMatch = html.match(/Latest Analysis:.*?Scanned: ([^<]+)</s);
    const timestamp = timestampMatch ? timestampMatch[1] : null;

    return {
      completed: hasLatestAnalysis,
      gapCount,
      errorCount,
      hasIssues: gapCount > 0 || errorCount > 0,
      timestamp
    };
  } catch (e) {
    return { completed: false, gapCount: 0, errorCount: 0, hasIssues: false, timestamp: null };
  }
}

/**
 * Start adaptive polling for analysis completion with progress tracking
 * Battery-friendly: starts fast (1s), backs off to 5s, pauses when tab hidden
 * Shows real-time progress based on analysis pipeline stages
 */
export async function startPollingForCompletion() {
  // Get initial teacher info to capture starting state
  const initialInfo = await checkTeacherInfo();
  if (!initialInfo.success) {
    addMessage("❌ Error starting analysis tracking");
    return;
  }

  // Record start time and initial analysis timestamps
  const startTime = Date.now();
  const initialAnalysisTimestamps = {};
  initialInfo.students.forEach(student => {
    initialAnalysisTimestamps[student.id] = student.last_analysis_at;
  });

  let attempts = 0;
  let currentInterval = POLLING.INITIAL_INTERVAL;
  let isPageVisible = !document.hidden;
  let timeoutId = null;
  let messageRotationIndex = 0;
  let lastTipUpdate = 0;

  // Monitor page visibility to pause polling when hidden (saves battery)
  const visibilityHandler = () => {
    isPageVisible = !document.hidden;
    if (isPageVisible && timeoutId === null) {
      scheduleNextPoll();
    }
  };

  if (POLLING.PAUSE_WHEN_HIDDEN) {
    document.addEventListener('visibilitychange', visibilityHandler);
  }

  const poll = async () => {
    // Skip polling if page is hidden and battery saving is enabled
    if (!isPageVisible && POLLING.PAUSE_WHEN_HIDDEN) {
      scheduleNextPoll();
      return;
    }

    attempts++;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);

    // Check for completion
    const info = await checkTeacherInfo();
    let newAnalysisFound = false;

    if (info.success) {
      // Check if any student has a new analysis
      for (const student of info.students) {
        const initial = initialAnalysisTimestamps[student.id];
        const current = student.last_analysis_at;

        if (current && current !== initial) {
          newAnalysisFound = true;
          break;
        }
      }
    }

    if (newAnalysisFound) {
      // Analysis complete!
      cleanup();
      removeProgressUI();

      // Get final results from reports page
      const status = await checkAnalysisStatus();

      const dashboardUrl = `${API.REPORTS}/${TEACHER_PHONE}`;
      const dashboardLink = `
        <div style="margin-top: 10px; padding: 12px; background: #25D366; border-radius: 10px; text-align: center;">
          <a href="${dashboardUrl}" target="_blank" style="color: white; text-decoration: none; font-weight: bold; display: block;">
            📊 VIEW FULL REPORT
          </a>
        </div>
      `;

      // Show contextual message based on findings
      if (status.gapCount > 0) {
        addMessage(`✅ Analysis complete! ${status.gapCount} learning gap${status.gapCount > 1 ? 's' : ''} identified.`);
      } else if (status.errorCount > 0) {
        addMessage(`⚠️ Analysis complete! Errors found. Check report for recommendations.`);
      } else {
        addMessage(`✅ Analysis complete! No issues found - excellent work!`);
      }

      addMessage(dashboardLink);
    } else if (attempts >= POLLING.MAX_ATTEMPTS) {
      // Timeout
      cleanup();
      removeProgressUI();
      addMessage("⏱️ Analysis is taking longer than expected. Please check back in a moment.");

      const dashboardUrl = `${API.REPORTS}/${TEACHER_PHONE}`;
      const dashboardLink = `
        <div style="margin-top: 10px; padding: 12px; background: #FFA500; border-radius: 10px; text-align: center;">
          <a href="${dashboardUrl}" target="_blank" style="color: white; text-decoration: none; font-weight: bold; display: block;">
            📊 CHECK DASHBOARD
          </a>
        </div>
      `;
      addMessage(dashboardLink);
    } else {
      // Update progress UI
      const stage = getProgressStage(elapsed);

      // Rotate tip message every 8 seconds
      let tip = null;
      if (elapsed - lastTipUpdate >= 8) {
        tip = WAIT_MESSAGES[messageRotationIndex % WAIT_MESSAGES.length];
        messageRotationIndex++;
        lastTipUpdate = elapsed;
      }

      updateProgressUI(stage.progress, stage.name, stage.icon, elapsed, tip);

      // Adaptive backoff: increase interval for battery savings
      currentInterval = Math.min(
        currentInterval * POLLING.BACKOFF_MULTIPLIER,
        POLLING.MAX_INTERVAL
      );
      scheduleNextPoll();
    }
  };

  const scheduleNextPoll = () => {
    timeoutId = setTimeout(poll, currentInterval);
  };

  const cleanup = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    document.removeEventListener('visibilitychange', visibilityHandler);
  };

  // Store cleanup function for external cancellation
  setAnalysisPollingInterval({ stop: cleanup });

  // Start first poll immediately
  poll();
}

/**
 * Open reports page in new tab
 */
export function openReports() {
  const reportsUrl = `${API.REPORTS}/${encodeURIComponent(TEACHER_PHONE)}`;
  window.open(reportsUrl, '_blank');
}

/**
 * Initialize demo by loading teacher info
 */
export async function initDemo() {
  try {
    const info = await apiClient.get(`${API.TEACHER_INFO}?teacher_phone=${TEACHER_PHONE}`);
    if (info.teacher && info.teacher.onboarded) {
      document.getElementById('statusBadge').textContent = '✅ Onboarded';
    }
  } catch (error) {
    console.error('Error loading teacher info:', error);
  }
}

/**
 * Handle keyboard input (Enter to send)
 * @param {KeyboardEvent} event - Keyboard event
 */
export function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Expose functions to global scope for onclick handlers
// TODO: Replace with event delegation in future refactor
window.sendQuickMessage = sendQuickMessage;
window.openReports = openReports;
window.handleImageSelect = handleImageSelect;
window.sendButtonClick = sendButtonClick;
