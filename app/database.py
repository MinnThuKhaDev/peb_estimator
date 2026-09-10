import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# In production set DATABASE_URL to your free cloud Postgres connection string
# (e.g. from Neon or Supabase), which already looks like:
#   postgresql://user:password@host/dbname?sslmode=require
# Locally, with no DATABASE_URL set, it falls back to a SQLite file so
# development still works without any setup.
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./peb_estimator.db")

connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    from . import models  # noqa: F401  (register model with Base metadata)
    from .security import hash_password
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed the admin account once. Password is hashed immediately —
        # the plaintext is never written to disk or the database.
        if db.query(models.User).count() == 0:
            admin_password = os.getenv("ADMIN_INITIAL_PASSWORD", "PEB77777@mmvm")
            db.add(models.User(
                username="admin",
                password_hash=hash_password(admin_password),
                is_admin=True,
            ))
            db.commit()

        if db.query(models.Project).count() == 0:
            seeds = [
                models.Project(
                    name="M-P02570/25 Thilawa Open Yard (Canopy, open)",
                    width=45.72, length=95.098, eave_height=10, wind_speed=130,
                    live_load=0.57, seismic_zone="Zone 3", occupancy="II",
                    enclosure="Open", frame_type="CS", total_weight=146249,
                ),
                models.Project(
                    name="M-J02570/25 150x302 Warehouse (Enclosed, mezz+crane+canopy)",
                    width=45.72, length=91.815, eave_height=11, wind_speed=130,
                    live_load=0.57, seismic_zone="Zone 3", occupancy="II",
                    enclosure="Enclosed", frame_type="MS1", total_weight=208045,
                ),
            ]
            db.add_all(seeds)
            db.commit()
    finally:
        db.close()
