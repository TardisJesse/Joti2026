# Railway deployment

Deploy CyberJoti as four services in one Railway project:

1. PostgreSQL – Railway database template; keep private.
2. Redis – Railway database template; keep private.
3. backend – GitHub source root /backend.
4. frontend – GitHub source root /frontend; generate the public player domain.

## Backend variables

Set DATABASE_URL to the Postgres DATABASE_URL reference, REDIS_URL to the Redis
DATABASE_URL reference, a long random SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES=480,
CORS_ORIGINS=https://your-frontend-domain, and PORT=8000.

The production image applies Alembic migrations but deliberately does not seed
demo accounts or game data.

## Frontend variables

Set BACKEND_URL=http://backend.railway.internal:8000 in the frontend service.
The frontend is a compiled Vue build served by Caddy. Caddy proxies /api and
/ws to the private backend service, so players use a single public origin.

## First release

1. Push this repository to a GitHub repository.
2. Create the four Railway services above, each from that repository where applicable.
3. Set the variables, deploy, then generate the frontend domain.
4. Use the admin UI to create production users and objects. Do not use local
   demo credentials in production.
