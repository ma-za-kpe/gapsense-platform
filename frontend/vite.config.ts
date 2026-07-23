import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const securityHeaders = {
  "Content-Security-Policy":
    "default-src 'self'; base-uri 'self'; connect-src 'self' ws:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self'",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
} as const;

const viteDevelopmentClientHash = "sha256-Z2/iFzh9VMlVkEOar1f/oSHWwQk3ve1qk/C2WdsC4Xk="; // pragma: allowlist secret -- public CSP source hash

const developmentSecurityHeaders = {
  ...securityHeaders,
  "Content-Security-Policy": `default-src 'self'; base-uri 'self'; connect-src 'self' ws:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self' '${viteDevelopmentClientHash}'; style-src 'self' 'unsafe-inline'`,
} as const;

export default defineConfig({
  plugins: [react()],
  cacheDir: "/tmp/gapsense-vite-cache",
  server: {
    host: "0.0.0.0",
    allowedHosts: ["frontend"],
    port: 3000,
    strictPort: true,
    headers: developmentSecurityHeaders,
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET ?? "http://web:8000",
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
    watch: {
      usePolling: true,
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    headers: securityHeaders,
  },
  build: {
    emptyOutDir: true,
    outDir: process.env.VITE_OUT_DIR ?? "dist",
    sourcemap: false,
    target: "es2020",
  },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    clearMocks: true,
    restoreMocks: true,
    coverage: {
      provider: "v8",
      enabled: true,
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.d.ts"],
      reporter: ["text", "json-summary"],
      reportsDirectory: "/tmp/gapsense-frontend-coverage",
      thresholds: {
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100,
      },
    },
  },
});
