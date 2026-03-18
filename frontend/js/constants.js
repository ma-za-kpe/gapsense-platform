/**
 * Constants - GapSense Demo Configuration
 * Mobile-optimized constants for WhatsApp demo
 */

export const TEACHER_PHONE = '+233501234567';
export const TOTAL_SLIDES = 12;

// API endpoints
export const API = {
  MESSAGE: '/demo/api/message',
  UPLOAD_IMAGE: '/demo/api/upload-image',
  TEACHER_INFO: '/demo/api/teacher-info',
  REPORTS: '/demo/reports'
};

// File upload limits (mobile-optimized for 3G networks)
export const FILE_LIMITS = {
  MAX_SIZE: 5 * 1024 * 1024, // 5MB
  ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/jpg']
};

// Polling configuration (battery-friendly for mobile)
export const POLLING = {
  INTERVAL: 2000,           // 2 seconds
  MAX_ATTEMPTS: 30,         // 60 seconds total
  SWIPE_THRESHOLD: 50       // 50px swipe to trigger slide change
};
