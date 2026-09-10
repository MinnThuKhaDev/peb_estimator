from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    totp_secret = Column(String, nullable=True)      # set once user enables 2FA
    totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    width = Column(Float, nullable=False)
    length = Column(Float, nullable=False)
    eave_height = Column(Float, nullable=False)
    wind_speed = Column(Float, default=130)
    live_load = Column(Float, default=0.57)
    seismic_zone = Column(String, default="")
    occupancy = Column(String, default="II")
    enclosure = Column(String, default="Enclosed")
    frame_type = Column(String, default="")
    total_weight = Column(Float, nullable=False)  # actual/quoted weight in kg
