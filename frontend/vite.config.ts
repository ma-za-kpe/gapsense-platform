import { createHash } from "node:crypto";

import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

import {
  buildRobotsText,
  buildSearchScriptSource,
  buildSitemapXml,
  injectSearchHead,
  resolveSearchPublication,
} from "./src/seo/publication";

const searchPublication = resolveSearchPublication(
  process.env.GAPSENSE_SEARCH_INDEXING,
  process.env.GAPSENSE_PUBLIC_ORIGIN,
);
const searchScriptSource = buildSearchScriptSource(searchPublication, (value) =>
  createHash("sha256").update(value).digest("base64"),
);
const productionScriptSources = ["'self'", searchScriptSource].filter((source) => source !== "");

const securityHeaders = {
  "Content-Security-Policy": `default-src 'self'; base-uri 'self'; connect-src 'self' ws:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src ${productionScriptSources.join(" ")}; style-src 'self'`,
  "Cross-Origin-Opener-Policy": "same-origin",
  "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=()",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
} as const;

const viteDevelopmentClientHash = "sha256-Z2/iFzh9VMlVkEOar1f/oSHWwQk3ve1qk/C2WdsC4Xk="; // pragma: allowlist secret -- public CSP source hash
const developmentScriptSources = [
  ...productionScriptSources,
  `'${viteDevelopmentClientHash}'`,
].join(" ");

const developmentSecurityHeaders = {
  ...securityHeaders,
  "Content-Security-Policy": `default-src 'self'; base-uri 'self'; connect-src 'self' ws:; font-src 'self'; form-action 'self'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src ${developmentScriptSources}; style-src 'self' 'unsafe-inline'`,
} as const;

function searchPublicationPlugin(): Plugin {
  const robotsText = buildRobotsText(searchPublication);
  const sitemapXml = buildSitemapXml(searchPublication);

  return {
    name: "gapsense-search-publication",
    transformIndexHtml: (html) => injectSearchHead(html, searchPublication),
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const requestPath = request.url?.split("?", 1)[0];
        const bodyAllowed = request.method !== "HEAD";
        if (requestPath === "/robots.txt") {
          response.statusCode = 200;
          response.setHeader("Cache-Control", "no-store");
          response.setHeader("Content-Type", "text/plain; charset=utf-8");
          response.end(bodyAllowed ? robotsText : undefined);
          return;
        }
        if (requestPath === "/sitemap.xml") {
          response.setHeader("Cache-Control", "no-store");
          if (sitemapXml === null) {
            response.statusCode = 404;
            response.setHeader("Content-Type", "text/plain; charset=utf-8");
            response.end(bodyAllowed ? "Not found\n" : undefined);
            return;
          }
          response.statusCode = 200;
          response.setHeader("Content-Type", "application/xml; charset=utf-8");
          response.end(bodyAllowed ? sitemapXml : undefined);
          return;
        }
        next();
      });
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "robots.txt", source: robotsText });
      this.emitFile({
        type: "asset",
        fileName: ".search-script-source",
        source: searchScriptSource,
      });
      if (sitemapXml !== null) {
        this.emitFile({ type: "asset", fileName: "sitemap.xml", source: sitemapXml });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), searchPublicationPlugin()],
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
