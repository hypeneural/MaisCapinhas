Migrations live here (Alembic). Initialize when ready:

- alembic init migrations
- configure alembic.ini with DATABASE_URL
- alembic revision --autogenerate -m "init"
- alembic upgrade head
