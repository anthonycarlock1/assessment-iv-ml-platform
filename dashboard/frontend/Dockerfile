# Uses Node to install frontend dependencies and compile the React app.
FROM node:22-alpine AS build
WORKDIR /frontend
COPY dashboard/frontend/package*.json ./
# Installs the exact versions in the lockfile.
RUN npm ci
COPY dashboard/frontend/ ./
# Creates static production HTML, JavaScript, and CSS.
RUN npm run build
# Uses a smaller nginx image to serve the compiled app.
FROM nginx:1.28-alpine
# Installs the API proxy and health/readiness configuration.
COPY dashboard/frontend/nginx.conf /etc/nginx/conf.d/default.conf
# Copies build output into nginx’s web directory.
COPY --from=build /frontend/dist /usr/share/nginx/html
# Documents port 80.
EXPOSE 80
