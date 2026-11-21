# syntax=docker/dockerfile:1

# ── build: type-check and bundle the SPA
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ── run: static files + reverse proxy to the backend, as a non-root user (uid 101)
FROM nginxinc/nginx-unprivileged:1.29-alpine
# Where /api and /socket.io are proxied. Scheme + host + port, no trailing slash.
ENV BACKEND_URL=http://backend:8000
# The image's entrypoint renders /etc/nginx/templates/*.template with envsubst (only defined env vars are replaced).
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
