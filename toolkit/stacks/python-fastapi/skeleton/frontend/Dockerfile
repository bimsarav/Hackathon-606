# Multi-stage image: Node builds the SPA, nginx serves it and proxies /api. Versions: docs/architecture/COMPATIBILITY_MATRIX.md
ARG NODE_IMAGE=node:26.13.1-alpine
FROM ${NODE_IMAGE} AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.30.7-alpine
# Security: apply Alpine updates published after the base image, and run as the unprivileged nginx user
# (PID file in /tmp, cache owned by nginx, listen on 8080; see nginx.conf).
RUN apk upgrade --no-cache \
 && sed -i -e '/^user /d' -e 's,^pid .*,pid /tmp/nginx.pid;,' /etc/nginx/nginx.conf \
 && chown -R nginx:nginx /var/cache/nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
