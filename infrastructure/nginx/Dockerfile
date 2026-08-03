FROM node:22-alpine AS frontend-builder

WORKDIR /workspace

COPY package.json package-lock.json pnpm-workspace.yaml tsconfig.base.json ./
COPY apps ./apps
COPY modules ./modules
COPY packages ./packages

RUN npm ci

ARG VITE_PUBLIC_API_BASE_URL
ARG VITE_ADMIN_API_BASE_URL
ARG VITE_ENABLE_DYNAMIC_BACKDROP=true
ARG VITE_ADMIN_BASE_PATH=/admin/

ENV VITE_PUBLIC_API_BASE_URL=${VITE_PUBLIC_API_BASE_URL}
ENV VITE_ADMIN_API_BASE_URL=${VITE_ADMIN_API_BASE_URL}
ENV VITE_ENABLE_DYNAMIC_BACKDROP=${VITE_ENABLE_DYNAMIC_BACKDROP}

RUN npm run build:web

WORKDIR /workspace/apps/admin
ENV VITE_APP_BASE_PATH=${VITE_ADMIN_BASE_PATH}
RUN npm run build

FROM nginx:1.27-alpine

COPY infrastructure/nginx/docker-entrypoint.d/40-render-site.sh /docker-entrypoint.d/40-render-site.sh
COPY infrastructure/nginx/templates/site.http.conf.template /etc/nginx/templates/site.http.conf.template
COPY infrastructure/nginx/templates/site.https.conf.template /etc/nginx/templates/site.https.conf.template
COPY --from=frontend-builder /workspace/apps/web/dist/ /usr/share/nginx/html/public/
COPY --from=frontend-builder /workspace/apps/admin/dist/ /usr/share/nginx/html/admin/

RUN chmod +x /docker-entrypoint.d/40-render-site.sh \
    && mkdir -p /var/www/certbot /etc/letsencrypt/live
