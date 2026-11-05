# Imagen del frontend React (Vite dev server con hot reload)
FROM node:24-alpine

WORKDIR /app

# Solo manifestos primero: la capa de dependencias se cachea mientras no cambien
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# --host 0.0.0.0 expone el server fuera del contenedor (el puerto sale por compose)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
