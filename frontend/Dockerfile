# syntax=docker/dockerfile:1.7

FROM node:22.23.1-alpine3.23 AS dependencies

ENV NODE_ENV=development \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /workspace

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

RUN chown node:node /workspace


FROM dependencies AS development

COPY --chown=node:node . .

USER node

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]


FROM dependencies AS build

COPY . .

ARG GAPSENSE_PUBLIC_ORIGIN=
ARG GAPSENSE_SEARCH_INDEXING=hold
ENV GAPSENSE_PUBLIC_ORIGIN=${GAPSENSE_PUBLIC_ORIGIN} \
    GAPSENSE_SEARCH_INDEXING=${GAPSENSE_SEARCH_INDEXING}

RUN npm run build


FROM nginxinc/nginx-unprivileged:1.29.5-alpine3.23 AS production

ENV NGINX_ENTRYPOINT_QUIET_LOGS=1

USER root

COPY nginx.conf /tmp/gapsense-nginx.conf
COPY --from=build /workspace/dist /usr/share/nginx/html

RUN search_script_source="$(cat /usr/share/nginx/html/.search-script-source)" \
    && sed \
        "s|__GAPSENSE_SEARCH_SCRIPT_SOURCE__|${search_script_source}|g" \
        /tmp/gapsense-nginx.conf \
        > /etc/nginx/conf.d/default.conf \
    && rm \
        /tmp/gapsense-nginx.conf \
        /usr/share/nginx/html/.search-script-source

USER 101

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1


FROM mcr.microsoft.com/playwright:v1.61.1-noble AS browser-tests

ENV CI=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /workspace

COPY package.json package-lock.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

COPY --chown=pwuser:pwuser playwright.config.ts ./
COPY --chown=pwuser:pwuser e2e ./e2e

USER pwuser

CMD ["npm", "run", "test:e2e"]
