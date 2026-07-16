#!/bin/sh
set -eu

cd /var/www

git fetch origin main
git reset --hard origin/main
