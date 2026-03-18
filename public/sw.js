/**
 * Service Worker - GapSense Demo
 * Offline support and caching for Ghana's unreliable networks
 */

const CACHE_VERSION = 'gapsense-v1.0.0';
const CACHE_NAME = `${CACHE_VERSION}`;

// Assets to cache immediately on install
const STATIC_ASSETS = [
  '/',
  '/demo.html',
  '/frontend/css/demo.css',
  '/frontend/css/base/_variables.css',
  '/frontend/css/base/_reset.css',
  '/frontend/css/layouts/demo.css',
  '/frontend/css/components/slides.css',
  '/frontend/css/components/whatsapp.css',
  '/frontend/js/main.js',
  '/frontend/js/constants.js',
  '/frontend/js/state.js',
  '/frontend/js/ui.js',
  '/frontend/js/slides.js',
  '/frontend/js/mobile.js',
  '/frontend/js/api.js',
  '/frontend/js/APIClient.js'
];

// API routes that should always go to network (no caching)
const API_ROUTES = [
  '/demo/api/message',
  '/demo/api/upload-image',
  '/demo/api/teacher-info',
  '/demo/reports/'
];

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[Service Worker] Installed successfully');
        // Activate immediately
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Service Worker] Installation failed:', error);
      })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[Service Worker] Activated successfully');
        // Take control immediately
        return self.clients.claim();
      })
  );
});

/**
 * Fetch event - serve cached assets when offline
 * Strategy:
 * - API routes: Network only (always fresh data)
 * - Static assets: Cache first, fallback to network
 * - Other requests: Network first, fallback to cache
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // Strategy 1: API routes - Network only
  if (API_ROUTES.some(route => url.pathname.includes(route))) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // Return offline response for API calls
          return new Response(
            JSON.stringify({
              success: false,
              error: 'You are offline. Please check your connection.'
            }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // Strategy 2: Static assets - Cache first
  if (STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches.match(request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }

          // Not in cache, fetch from network
          return fetch(request)
            .then((networkResponse) => {
              // Cache the new response
              if (networkResponse && networkResponse.status === 200) {
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(request, networkResponse.clone());
                });
              }
              return networkResponse;
            });
        })
    );
    return;
  }

  // Strategy 3: Other requests - Network first, fallback to cache
  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        // Cache successful responses
        if (networkResponse && networkResponse.status === 200) {
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, networkResponse.clone());
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Network failed, try cache
        return caches.match(request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }

            // No cache available, return offline page
            return new Response(
              '<html><body><h1>You are offline</h1><p>Please check your internet connection.</p></body></html>',
              {
                status: 503,
                headers: { 'Content-Type': 'text/html' }
              }
            );
          });
      })
  );
});

/**
 * Message event - handle messages from clients
 */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_VERSION });
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME).then(() => {
      event.ports[0].postMessage({ success: true });
    });
  }
});

console.log('[Service Worker] Loaded successfully');
