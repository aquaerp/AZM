#!/bin/sh
set -eu

mkdir -p /app/logs /app/media
chown -R azm:azm /app/logs /app/media

exec gosu azm "$@"
