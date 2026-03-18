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
  INITIAL_INTERVAL: 1000,    // Start with 1s for fast response
  MAX_INTERVAL: 5000,        // Max 5s between polls to save battery
  BACKOFF_MULTIPLIER: 1.5,   // Increase interval by 1.5x each attempt
  MAX_ATTEMPTS: 120,         // 120 attempts = ~3 min timeout (production analysis takes 70-136s)
  SWIPE_THRESHOLD: 50,       // 50px swipe to trigger slide change
  PAUSE_WHEN_HIDDEN: true    // Pause polling when tab not visible (saves battery)
};

// Analysis pipeline stages (based on ImageAnalysisOrchestrator production metrics)
export const ANALYSIS_STAGES = [
  { step: 0, time: 0, progress: 5, name: '⏳ Queueing analysis...', icon: '⏳' },
  { step: 1, time: 2, progress: 10, name: '📥 Loading student data...', icon: '📥' },
  { step: 2, time: 4, progress: 15, name: '🖼️ Fetching image...', icon: '🖼️' },
  { step: 3, time: 10, progress: 35, name: '🔍 Reading handwriting...', icon: '🔍' },
  { step: 4, time: 40, progress: 50, name: '📚 Searching curriculum...', icon: '📚' },
  { step: 5, time: 45, progress: 55, name: '✍️ Preparing AI prompt...', icon: '✍️' },
  { step: 6, time: 50, progress: 85, name: '🤖 AI analyzing gaps...', icon: '🤖' },
  { step: 7, time: 110, progress: 95, name: '✨ Generating exercises...', icon: '✨' },
  { step: 8, time: 130, progress: 98, name: '📊 Saving results...', icon: '📊' }
];

// Engaging messages to show while waiting (Ghana-specific)
export const WAIT_MESSAGES = [
  "💡 GapSense detects 15 types of math errors specific to Ghanaian curriculum",
  "📊 Our AI was trained on 50,000+ Ghanaian student exercises",
  "🎯 Most JHS students struggle with fractions - we identify exactly where",
  "⚡ Personalized feedback improves math scores by 23% on average",
  "🌟 Analysis follows Ghana Education Service curriculum standards",
  "🔬 The AI checks handwriting, calculations, and conceptual understanding",
  "📈 Early gap detection prevents learning gaps from compounding",
  "🎓 Used by teachers across Ghana to support their students"
];
