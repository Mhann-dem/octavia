Alembic migrations for octavia-backend

How to generate the initial migration:

1. Ensure `DATABASE_URL` is set (or rely on the default sqlite dev.db).

```powershell
# from octavia-backend folder
setx DATABASE_URL "sqlite:///./dev.db"
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

If you prefer a single-session local run instead of setx, use PowerShell environment variable for the session:

```powershell
$env:DATABASE_URL = 'sqlite:///./dev.db'
alembic revision --autogenerate -m "initial"
alembic upgrade head
```
