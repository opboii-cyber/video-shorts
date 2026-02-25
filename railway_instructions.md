# Railway Deployment Instructions

Railway uses Nixpacks and Docker natively, making it very easy to deploy.

1. Create a Railway Project and link your GitHub repository.
2. Railway will detect the `docker-compose.yml` file. Usually, it's better to configure services individually in Railway.

### Service 1: PostgreSQL
- Add a new "Database" > "PostgreSQL" to your Railway project.

### Service 2: Redis
- Add a new "Database" > "Redis" to your Railway project.

### Service 3: FastAPI Backend
- Add a new "Service" > "GitHub Repo" and select your repository.
- **Root Directory:** `/backend`
- **Builder:** Dockerfile
- **Start Command:** `./start.sh web`
- **Variables:**
  - Copy variables from `.env.production.template`.
  - Link `DATABASE_URL` and `REDIS_URL` from the databases you just created.

### Service 4: Celery Worker
- Add another "Service" > "GitHub Repo" and select your repository again.
- **Root Directory:** `/backend`
- **Builder:** Dockerfile
- **Start Command:** `./start.sh worker`
- **Variables:**
  - Link the same `DATABASE_URL` and `REDIS_URL`.
  - Copy relevant API keys from your `.env.production.template`.

### Deploy
Railway will automatically build the Docker images and start your services!
