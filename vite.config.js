/**
 * Vite Configuration - GapSense Frontend
 * Mobile-first build optimization for Ghana's 3G networks
 */

import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  // Root directory
  root: 'public',

  // Base public path
  base: '/',

  // Build configuration
  build: {
    // Output directory (relative to root)
    outDir: '../dist',

    // Empty output directory before build
    emptyOutDir: true,

    // Target modern browsers but support ES2015 for broader compatibility
    target: 'es2015',

    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,        // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ['console.info', 'console.debug']
      },
      format: {
        comments: false            // Remove comments
      }
    },

    // CSS code splitting
    cssCodeSplit: true,

    // Generate source maps for debugging
    sourcemap: false, // Disable in production for smaller bundle

    // Rollup options
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'public/index.html'),
        demo: resolve(__dirname, 'public/demo.html'),
        developer: resolve(__dirname, 'public/developer.html')
      },
      output: {
        // Manual chunks for better caching
        manualChunks: {
          // Vendor chunk (future: add any npm packages here)
          'vendor': [],

          // API and networking
          'api': [
            './public/frontend/js/api.js',
            './public/frontend/js/APIClient.js'
          ],

          // UI components
          'ui': [
            './public/frontend/js/ui.js',
            './public/frontend/js/slides.js'
          ],

          // Mobile-specific
          'mobile': [
            './public/frontend/js/mobile.js',
            './public/frontend/js/state.js'
          ]
        },

        // Asset file names
        assetFileNames: (assetInfo) => {
          let extType = assetInfo.name.split('.').pop();
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return `assets/images/[name]-[hash][extname]`;
          }
          if (/css/i.test(extType)) {
            return `assets/css/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },

        // Chunk file names
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js'
      }
    },

    // Performance budgets
    chunkSizeWarningLimit: 200, // Warn if chunk > 200KB (Ghana 3G target)

    // Optimize dependencies
    commonjsOptions: {
      include: [/node_modules/]
    }
  },

  // Server configuration (for development)
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: false,
    open: '/demo.html',

    // CORS for API proxy
    cors: true,

    // Proxy API requests to backend (configurable via env)
    // Set VITE_API_BASE_URL in .env file or environment
    proxy: {
      '/demo/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/demo/reports': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },

  // Preview server (for production build testing)
  preview: {
    port: 4173,
    host: '0.0.0.0',
    strictPort: false,
    open: '/demo.html'
  },

  // Optimize deps
  optimizeDeps: {
    include: [],
    exclude: []
  },

  // CSS configuration
  css: {
    // PostCSS plugins
    postcss: {
      plugins: []
    },

    // CSS modules
    modules: {
      localsConvention: 'camelCase'
    }
  },

  // Plugins
  plugins: [],

  // Environment variables
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0')
  },

  // Logging
  logLevel: 'info',

  // Clear screen on file change
  clearScreen: true
});
