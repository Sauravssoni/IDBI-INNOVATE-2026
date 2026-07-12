FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:?required}
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL}

RUN npm run build


FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs \
    && chown -R nextjs:nodejs /app

USER nextjs
EXPOSE 3000
CMD ["npm", "run", "start"]
