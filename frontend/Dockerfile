FROM node:24-slim AS node-base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci


FROM node-base AS build

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80


FROM node-base AS dev

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
