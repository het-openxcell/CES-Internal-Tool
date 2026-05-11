FROM node:20-alpine

WORKDIR /app

# Install pnpm + static server
RUN npm install -g pnpm serve

# Copy dependencies
COPY package.json ./
COPY pnpm-lock.yaml* ./

# Install deps
RUN pnpm install || pnpm install --no-frozen-lockfile

# Copy source
COPY . .

# Build React (Vite) with env vars
#RUN if [ -f .env ]; then set -a && . ./.env && set +a; fi && pnpm build

# Expose Kubernetes target port
EXPOSE 3000

# Serve static build on port 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
