FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

FROM python:3.12-slim

WORKDIR /srv
COPY --from=build /app/dist ./

EXPOSE 5173

CMD ["python", "-m", "http.server", "5173", "--bind", "0.0.0.0"]
