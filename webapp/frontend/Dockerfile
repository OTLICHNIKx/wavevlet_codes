FROM node:22-alpine AS build
WORKDIR /app
COPY webapp/frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY webapp/frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY webapp/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
