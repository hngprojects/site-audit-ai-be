upstream fastapi_app {
    server 127.0.0.1:${APP_PORT};
}

server {
    listen 80;
    server_name ${SERVER_NAME};

    client_max_body_size 25m;
    keepalive_timeout 65;

    location /static/ {
        alias ${APP_ROOT}/app/static/;
    }

    location / {
        proxy_pass         http://fastapi_app;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection keep-alive;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_redirect     off;
    }

    error_log /var/log/nginx/${NGINX_LOG_PREFIX}_error.log;
    access_log /var/log/nginx/${NGINX_LOG_PREFIX}_access.log;
}
