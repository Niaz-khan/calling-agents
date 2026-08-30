# Multi-stage: build the React admin/landing frontend, then ship it from nginx.
FROM node:22-alpine AS frontend

WORKDIR /src
COPY frontend/package*.json ./
RUN npm config set fund false && npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=frontend /src/dist /usr/share/nginx/html
COPY nginx/prod.conf.template /etc/nginx/templates/prod.conf.template

# The stock default.conf also listens on :80 and would collide with the
# template-rendered site config.
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443