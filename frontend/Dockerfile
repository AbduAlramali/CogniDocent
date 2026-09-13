# Stage 1: Development
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173 80
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 2: Build
FROM development AS build
RUN npm run build

# Stage 3: Production
FROM nginx:stable-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html

# Custom Nginx configuration: SPA routing, 100MB upload limit for PDFs, and reverse proxy for /api/
RUN echo 'server { \
    listen 80; \
    client_max_body_size 100M; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000/; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_buffering off; \
        proxy_read_timeout 86400s; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["sh", "-c", "echo \"window._env_ = { VITE_API_URL: '${VITE_API_URL:-/api/v1}' };\" > /usr/share/nginx/html/env-config.js && exec nginx -g 'daemon off;'"]
