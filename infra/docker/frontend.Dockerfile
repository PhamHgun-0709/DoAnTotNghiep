FROM nginx:1.27-alpine

COPY infra/docker/nginx.webservice.conf /etc/nginx/conf.d/default.conf
COPY giao-dien/public /usr/share/nginx/html

EXPOSE 80
