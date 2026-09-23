# Frontend image: Vite dev server on Node 22 (package.json requires >=22).
FROM node:22-alpine

WORKDIR /app

# Copy manifests first so npm ci only re-runs when dependencies change.
COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# --host binds 0.0.0.0; without it Vite only listens inside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
