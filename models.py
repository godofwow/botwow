from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False)  # ID в Telegram
    username = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")  # user, project_manager, owner
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь с подключёнными сервисами
    services = relationship("ConnectedService", back_populates="user")

class ConnectedService(Base):
    __tablename__ = "connected_services"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_name = Column(String, nullable=False)  # Например, "Google Analytics"
    auth_token = Column(Text, nullable=False)  # OAuth-токен
    connected_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="services")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
