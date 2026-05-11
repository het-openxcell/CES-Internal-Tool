# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

RUN npm install -g pnpm

COPY package.json ./
COPY pnpm-lock.yaml* ./

RUN pnpm install --no-frozen-lockfile

COPY . .

RUN pnpm build

# Runtime Stage
FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
