# AI Verkenner frontend — local dev image (M2).
FROM node:20-slim

WORKDIR /app

# Install deps first for layer caching, then bring in the source.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Vite dev server, exposed on all interfaces so the host-mapped port works.
CMD ["npm", "run", "dev", "--", "--host"]
