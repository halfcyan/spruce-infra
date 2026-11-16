URL=https://outline.willowidk.dev
PORT=3000
FORCE_HTTPS=true

SECRET_KEY={{ op://spruce/outline/SECRET_KEY }}
UTILS_SECRET={{ op://spruce/outline/UTILS_SECRET }}

POSTGRES_USER=outline
POSTGRES_DB=outline
POSTGRES_PASSWORD={{ op://spruce/outline/DB_PASSWORD }}
DATABASE_HOST=outline-db
DATABASE_PORT=5432
DATABASE_NAME=outline
DATABASE_USER=outline
DATABASE_PASSWORD={{ op://spruce/outline/DB_PASSWORD }}
PGSSLMODE=disable

REDIS_URL=redis://outline-redis:6379

FILE_STORAGE=local
FILE_STORAGE_LOCAL_ROOT_DIR=/var/lib/outline/data
FILE_STORAGE_UPLOAD_MAX_SIZE=262144000

OIDC_ISSUER_URL=https://auth.willowidk.dev/oidc
OIDC_CLIENT_ID=outline
OIDC_CLIENT_SECRET={{ op://spruce/outline/OIDC_CLIENT_SECRET }}
OIDC_LOGOUT_URI=https://auth.willowidk.dev/oidc/session/end
OIDC_DISPLAY_NAME=VoidAuth
OIDC_USERNAME_CLAIM=preferred_username
OIDC_SCOPES=openid profile email
