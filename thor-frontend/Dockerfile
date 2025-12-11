# syntax=docker/dockerfile:1

# ---------- Build Stage ----------
FROM node:20-alpine AS build

WORKDIR /app

# Install deps (use cache as much as possible)
COPY thor-frontend/package*.json ./
RUN npm install

# Copy the rest of the source and build
COPY thor-frontend/ ./
# Vite: outputs to dist/  | CRA: outputs to build/
RUN npm run build

# ---------- Run Stage (Nginx) ----------
FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy build output from previous stage (/dist for Vite)
COPY --from=build /app/dist /usr/share/nginx/html

# Add our custom Nginx config
COPY docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
