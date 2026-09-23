FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm

WORKDIR /usr/src/app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY app ./app

EXPOSE 8080
USER node
CMD ["node", "app/server.mjs"]
