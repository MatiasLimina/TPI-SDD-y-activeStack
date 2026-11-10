FROM node:24-slim

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

EXPOSE 5173
# Servidor de desarrollo de Vite: no apto para producción (design D10)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
