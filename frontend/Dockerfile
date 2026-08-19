FROM node:22-alpine AS development

ARG UID=1000
ARG GID=1000

RUN deluser --remove-home node \
    && addgroup -g ${GID} pacelab \
    && adduser -D -u ${UID} -G pacelab pacelab

WORKDIR /app

COPY package.json package-lock.json* ./
COPY scripts ./scripts
RUN chmod +x /app/scripts/entrypoint.sh \
    && npm install \
    && chown -R pacelab:pacelab /app

USER pacelab

EXPOSE 5173

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS production

RUN adduser -D -H -u 1000 -s /sbin/nologin pacelab \
    && chown -R pacelab:pacelab /usr/share/nginx/html /var/cache/nginx /var/run /var/log/nginx

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

USER pacelab
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
