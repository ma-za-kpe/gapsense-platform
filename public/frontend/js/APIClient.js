/**
 * APIClient - Robust HTTP Client for 3G Networks
 * Optimized for Ghana's network conditions with retry logic and exponential backoff
 */

/**
 * @typedef {Object} APIClientConfig
 * @property {number} maxRetries - Maximum retry attempts (default: 3)
 * @property {number} timeout - Request timeout in ms (default: 30000)
 * @property {number} retryDelay - Initial retry delay in ms (default: 1000)
 * @property {boolean} exponentialBackoff - Use exponential backoff (default: true)
 */

/**
 * @typedef {Object} RequestOptions
 * @property {string} method - HTTP method (GET, POST, etc.)
 * @property {Object|FormData} body - Request body
 * @property {Object} headers - Request headers
 * @property {boolean} json - Auto parse JSON response (default: true)
 * @property {number} timeout - Override global timeout
 * @property {number} maxRetries - Override global max retries
 */

export class APIClient {
  /**
   * Create an API client instance
   * @param {APIClientConfig} config - Configuration options
   */
  constructor(config = {}) {
    this.maxRetries = config.maxRetries || 3;
    this.timeout = config.timeout || 30000; // 30s for 3G networks
    this.retryDelay = config.retryDelay || 1000; // 1s initial delay
    this.exponentialBackoff = config.exponentialBackoff !== false;

    // Track request metrics for monitoring
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      retriedRequests: 0
    };
  }

  /**
   * Make a GET request
   * @param {string} url - Request URL
   * @param {Object} options - Request options
   * @returns {Promise<any>} Response data
   */
  async get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  /**
   * Make a POST request
   * @param {string} url - Request URL
   * @param {Object|FormData} body - Request body
   * @param {Object} options - Request options
   * @returns {Promise<any>} Response data
   */
  async post(url, body, options = {}) {
    return this.request(url, { ...options, method: 'POST', body });
  }

  /**
   * Make a PUT request
   * @param {string} url - Request URL
   * @param {Object|FormData} body - Request body
   * @param {Object} options - Request options
   * @returns {Promise<any>} Response data
   */
  async put(url, body, options = {}) {
    return this.request(url, { ...options, method: 'PUT', body });
  }

  /**
   * Make a DELETE request
   * @param {string} url - Request URL
   * @param {Object} options - Request options
   * @returns {Promise<any>} Response data
   */
  async delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }

  /**
   * Main request method with retry logic
   * @param {string} url - Request URL
   * @param {RequestOptions} options - Request options
   * @returns {Promise<any>} Response data
   */
  async request(url, options = {}) {
    const maxRetries = options.maxRetries ?? this.maxRetries;
    const timeout = options.timeout ?? this.timeout;

    this.metrics.totalRequests++;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Create timeout controller
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        // Build request options
        const fetchOptions = {
          method: options.method || 'GET',
          signal: controller.signal,
          headers: options.headers || {}
        };

        // Handle body (JSON or FormData)
        if (options.body) {
          if (options.body instanceof FormData) {
            fetchOptions.body = options.body;
            // Don't set Content-Type for FormData (browser sets it with boundary)
          } else {
            fetchOptions.body = JSON.stringify(options.body);
            fetchOptions.headers['Content-Type'] = 'application/json';
          }
        }

        // Make request
        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);

        // Check response status
        if (!response.ok) {
          throw new APIError(
            `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            await this._parseErrorBody(response)
          );
        }

        // Parse response
        const data = options.json !== false
          ? await response.json()
          : await response.text();

        this.metrics.successfulRequests++;

        // Log retry success if this wasn't first attempt
        if (attempt > 0) {
          console.log(`✅ Request succeeded after ${attempt} ${attempt === 1 ? 'retry' : 'retries'}: ${url}`);
        }

        return data;

      } catch (error) {
        // Clear timeout if still pending
        clearTimeout(timeoutId);

        // Check if this is the last attempt
        const isLastAttempt = attempt === maxRetries;

        // Log retry attempt
        if (!isLastAttempt && this._shouldRetry(error)) {
          this.metrics.retriedRequests++;

          const delay = this._getRetryDelay(attempt);
          console.warn(
            `⚠️ Request failed (attempt ${attempt + 1}/${maxRetries + 1}). Retrying in ${delay}ms...`,
            { url, error: error.message }
          );

          await this._sleep(delay);
          continue;
        }

        // Last attempt failed or non-retryable error
        this.metrics.failedRequests++;

        // Enhance error with context
        const enhancedError = this._enhanceError(error, url, attempt + 1);
        throw enhancedError;
      }
    }
  }

  /**
   * Check if error should trigger a retry
   * @param {Error} error - Error object
   * @returns {boolean} Should retry
   */
  _shouldRetry(error) {
    // Retry on network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return true;
    }

    // Retry on timeout
    if (error.name === 'AbortError') {
      return true;
    }

    // Retry on 5xx server errors
    if (error instanceof APIError && error.status >= 500) {
      return true;
    }

    // Retry on 429 (Too Many Requests)
    if (error instanceof APIError && error.status === 429) {
      return true;
    }

    // Don't retry on 4xx client errors (except 429)
    if (error instanceof APIError && error.status >= 400 && error.status < 500) {
      return false;
    }

    // Default: retry
    return true;
  }

  /**
   * Calculate retry delay with exponential backoff
   * @param {number} attempt - Current attempt number (0-indexed)
   * @returns {number} Delay in milliseconds
   */
  _getRetryDelay(attempt) {
    if (!this.exponentialBackoff) {
      return this.retryDelay;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, ...
    // With jitter to prevent thundering herd
    const exponentialDelay = this.retryDelay * Math.pow(2, attempt);
    const jitter = Math.random() * 500; // 0-500ms jitter

    return Math.min(exponentialDelay + jitter, 10000); // Max 10s
  }

  /**
   * Sleep for specified milliseconds
   * @param {number} ms - Milliseconds to sleep
   * @returns {Promise<void>}
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Parse error response body
   * @param {Response} response - Fetch response
   * @returns {Promise<any>} Parsed error body
   */
  async _parseErrorBody(response) {
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return await response.text();
      }
    } catch (e) {
      return null;
    }
  }

  /**
   * Enhance error with additional context
   * @param {Error} error - Original error
   * @param {string} url - Request URL
   * @param {number} attempts - Number of attempts made
   * @returns {Error} Enhanced error
   */
  _enhanceError(error, url, attempts) {
    if (error instanceof APIError) {
      error.url = url;
      error.attempts = attempts;
      return error;
    }

    // Handle timeout
    if (error.name === 'AbortError') {
      return new APIError(
        `Request timeout after ${this.timeout}ms (${attempts} ${attempts === 1 ? 'attempt' : 'attempts'})`,
        408,
        null,
        url,
        attempts
      );
    }

    // Handle network error
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return new APIError(
        `Network error: Unable to connect (${attempts} ${attempts === 1 ? 'attempt' : 'attempts'})`,
        0,
        null,
        url,
        attempts
      );
    }

    // Generic error
    return new APIError(
      error.message,
      0,
      null,
      url,
      attempts
    );
  }

  /**
   * Get request metrics
   * @returns {Object} Metrics object
   */
  getMetrics() {
    return {
      ...this.metrics,
      successRate: this.metrics.totalRequests > 0
        ? (this.metrics.successfulRequests / this.metrics.totalRequests * 100).toFixed(1) + '%'
        : '0%'
    };
  }

  /**
   * Reset metrics
   */
  resetMetrics() {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      retriedRequests: 0
    };
  }
}

/**
 * Custom API Error class
 */
export class APIError extends Error {
  /**
   * Create an API error
   * @param {string} message - Error message
   * @param {number} status - HTTP status code
   * @param {any} body - Error response body
   * @param {string} url - Request URL
   * @param {number} attempts - Number of attempts made
   */
  constructor(message, status, body = null, url = null, attempts = 1) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.body = body;
    this.url = url;
    this.attempts = attempts;
  }

  /**
   * Get user-friendly error message
   * @returns {string} User-friendly message
   */
  getUserMessage() {
    // Network errors
    if (this.status === 0) {
      return '❌ No internet connection. Please check your network and try again.';
    }

    // Timeout
    if (this.status === 408) {
      return '⏱️ Request timed out. Please try again.';
    }

    // Server errors
    if (this.status >= 500) {
      return '❌ Server error. Please try again in a moment.';
    }

    // Client errors
    if (this.status === 400) {
      return '❌ Invalid request. Please check your input.';
    }

    if (this.status === 401) {
      return '🔒 Authentication required. Please log in again.';
    }

    if (this.status === 403) {
      return '🚫 Access denied. You don\'t have permission to do this.';
    }

    if (this.status === 404) {
      return '❓ Resource not found.';
    }

    if (this.status === 429) {
      return '⏸️ Too many requests. Please wait a moment and try again.';
    }

    // Default
    return `❌ Error: ${this.message}`;
  }
}

// Create default singleton instance optimized for Ghana 3G
export const apiClient = new APIClient({
  maxRetries: 3,
  timeout: 30000,      // 30s for 3G networks
  retryDelay: 1000,    // 1s initial delay
  exponentialBackoff: true
});
