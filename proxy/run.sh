#!/bin/sh

set -e
echo "APP_HOST is set to: $APP_HOST"
echo "APP_PORT is set to: $APP_PORT"

echo "Starting envsubst..."
envsubst < /etc/nginx/default.conf.tpl > /etc/nginx/conf.d/default.conf
echo "Configuration file created."
nginx -g 'daemon off;'
