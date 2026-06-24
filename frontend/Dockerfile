FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/*.html /usr/share/nginx/html/
COPY frontend/css /usr/share/nginx/html/css
COPY frontend/js /usr/share/nginx/html/js
COPY frontend/img /usr/share/nginx/html/img

EXPOSE 80

ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
