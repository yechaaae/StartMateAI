FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL
ARG VITE_CHAT_USER_ID
ARG VITE_KAKAO_MAP_KEY

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_CHAT_USER_ID=$VITE_CHAT_USER_ID
ENV VITE_KAKAO_MAP_KEY=$VITE_KAKAO_MAP_KEY

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM nginx:1.27-alpine

# 인증서 유무에 따라 entrypoint가 둘 중 하나를 conf.d/default.conf로 복사한다.
COPY nginx.http.conf /etc/nginx/available/http.conf
COPY nginx.https.conf /etc/nginx/available/https.conf
COPY docker-entrypoint.sh /docker-entrypoint-tls.sh
RUN chmod +x /docker-entrypoint-tls.sh

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443

ENTRYPOINT ["/docker-entrypoint-tls.sh"]
