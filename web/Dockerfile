FROM node:22.23.2-alpine AS dependencias
WORKDIR /app
# npm ci: instala exactamente lo del package-lock.json (que es obligatorio)
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22.23.2-alpine AS constructor
WORKDIR /app
# Destino de /api: queda fijo en la imagen al construir (next build)
ARG API_INTERNA=http://avicola-api:8000
ENV API_INTERNA=$API_INTERNA
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencias /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22.23.2-alpine AS ejecucion
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
# El servidor de Next escucha en la IP que diga HOSTNAME; en Docker, HOSTNAME es el
# id del contenedor y quedaria escuchando solo en una interfaz
ENV HOSTNAME=0.0.0.0
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=constructor /app/public ./public
COPY --from=constructor --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=constructor --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD wget -qO- http://127.0.0.1:3000/login >/dev/null || exit 1
CMD ["node", "server.js"]
