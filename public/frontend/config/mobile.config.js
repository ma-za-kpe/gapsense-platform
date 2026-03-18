/**
 * Mobile-First Configuration
 * GapSense Platform
 */

export const MOBILE_CONFIG = {
  // Responsive Breakpoints (mobile-first: min-width)
  breakpoints: {
    sm: '640px',   // Small tablets
    md: '768px',   // Tablets
    lg: '1024px',  // Small desktops
    xl: '1280px',  // Large desktops
    '2xl': '1536px' // Extra large screens
  },

  // Touch Target Specifications (Apple HIG + Material Design)
  touchTargets: {
    minSize: 44,        // Minimum 44x44px (Apple)
    comfortable: 48,    // Comfortable 48x48px (Material)
    minSpacing: 8       // Minimum 8px between targets
  },

  // Performance Budget
  performance: {
    maxBundleSize: 200 * 1024,      // 200KB max (gzipped)
    maxImageSize: 100 * 1024,       // 100KB per image
    maxInitialRequests: 10,          // Max HTTP requests on load
    targetFCP: 1500,                 // First Contentful Paint < 1.5s
    targetTTI: 3500,                 // Time to Interactive < 3.5s
    targetLCP: 2500,                 // Largest Contentful Paint < 2.5s
    minLighthouseScore: 90           // Minimum Lighthouse score
  },

  // Image Optimization
  images: {
    formats: ['webp', 'jpg', 'png'],  // Preferred formats (in order)
    quality: 85,                       // Default quality (85%)
    lazyLoadThreshold: 200,            // Load when 200px from viewport
    srcsetSizes: [320, 640, 960, 1280, 1920], // Responsive image sizes
    placeholderQuality: 10             // Blur placeholder quality
  },

  // Offline Support (PWA)
  pwa: {
    enabled: true,
    cacheStrategy: 'network-first',    // Network first, fallback to cache
    cacheName: 'gapsense-v1',
    maxAge: 7 * 24 * 60 * 60 * 1000,  // 7 days cache
    precache: [
      '/',
      '/demo',
      '/demo/curriculum',
      '/static/css/main.css',
      '/static/js/main.js'
    ]
  },

  // Gesture Support
  gestures: {
    swipeThreshold: 50,               // 50px minimum swipe distance
    swipeVelocity: 0.3,               // Minimum swipe velocity
    longPressDelay: 500,              // 500ms for long press
    doubleTapDelay: 300               // 300ms between taps
  },

  // Virtual Scrolling (for long lists)
  virtualScroll: {
    itemHeight: 80,                   // Default item height
    overscan: 3,                      // Render 3 extra items above/below
    threshold: 100                    // Enable when list > 100 items
  },

  // Network Optimization
  network: {
    retryAttempts: 3,                 // Retry failed requests 3 times
    retryDelay: 1000,                 // 1s delay between retries
    timeout: 10000,                   // 10s request timeout
    enableCompression: true           // Enable gzip/brotli
  },

  // Accessibility
  a11y: {
    enableAnnouncements: true,        // Screen reader announcements
    focusManagement: true,            // Keyboard navigation
    colorContrastRatio: 4.5,          // WCAG AA (4.5:1 for normal text)
    fontSize: {
      min: 14,                        // Minimum 14px
      default: 16,                    // Default 16px
      max: 24                         // Maximum 24px
    }
  },

  // Device Detection
  devices: {
    mobile: {
      maxWidth: 767,
      userAgents: ['iPhone', 'Android', 'Mobile']
    },
    tablet: {
      minWidth: 768,
      maxWidth: 1023,
      userAgents: ['iPad', 'Tablet']
    },
    desktop: {
      minWidth: 1024
    }
  },

  // Feature Detection
  features: {
    touchEvents: 'ontouchstart' in window,
    serviceWorker: 'serviceWorker' in navigator,
    webp: true, // Detected at runtime
    localStorage: true,
    indexedDB: true
  }
};

export default MOBILE_CONFIG;
