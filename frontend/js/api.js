/**
 * API Module - GapSense Demo
 * All API calls, image upload, polling, and teacher info
 */

import { API, FILE_LIMITS, TEACHER_PHONE, POLLING } from './constants.js';
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
 * Start polling for analysis completion (battery-friendly 2s interval)
 */
export async function startPollingForCompletion() {
  const initialStatus = await checkAnalysisStatus();
  setInitialAnalysisTimestamp(initialStatus.timestamp);

  let attempts = 0;

  const pollingInterval = setInterval(async () => {
    attempts++;
    const status = await checkAnalysisStatus();

    // Check if a NEW analysis completed (timestamp changed OR analysis just appeared)
    const isNewAnalysis = status.completed && (
      !initialAnalysisTimestamp ||
      status.timestamp !== initialAnalysisTimestamp
    );

    if (isNewAnalysis) {
      clearInterval(pollingInterval);

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
      clearInterval(pollingInterval);
      addMessage("⏱️ Analysis is taking longer than expected. Please check back in a moment.");

      // Still provide dashboard link even on timeout
      const dashboardUrl = `${API.REPORTS}/${TEACHER_PHONE}`;
      const dashboardLink = `
        <div style="margin-top: 10px; padding: 12px; background: #FFA500; border-radius: 10px; text-align: center;">
          <a href="${dashboardUrl}" target="_blank" style="color: white; text-decoration: none; font-weight: bold; display: block;">
            📊 CHECK DASHBOARD
          </a>
        </div>
      `;
      addMessage(dashboardLink);
    }
  }, POLLING.INTERVAL);

  setAnalysisPollingInterval(pollingInterval);
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
