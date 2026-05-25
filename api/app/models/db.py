"""
SQLAlchemy Database Models and Connection

This module defines all database models used in the Ad Analytics application.
Models are used by Alembic for migrations and by the API for data operations.
"""

import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


def resolve_database_url() -> str:
    """Build the SQLAlchemy URL from env vars without hardcoding credentials."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
    port = os.getenv("DB_PORT", "5432").strip() or "5432"
    name = os.getenv("DB_NAME", "ad_analytics").strip() or "ad_analytics"
    user = os.getenv("DB_USER", "postgres").strip() or "postgres"
    password = os.getenv("DB_PASSWORD", "").strip()

    auth_segment = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql+psycopg://{auth_segment}{host}:{port}/{name}"

# Database URL from environment
DATABASE_URL = resolve_database_url()

# Create engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# SessionLocal for dependency injection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for declarative models
Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst")  # analyst, admin, guest
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """User session tracking."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Prediction(Base):
    """ML model predictions."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    campaign_id = Column(String(100), index=True)
    model_type = Column(String(100))  # conversion_predictor, campaign_classifier
    input_features = Column(JSON)  # Store input data
    prediction = Column(JSON)  # Prediction results
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="predictions")


class UploadLog(Base):
    """Data upload history."""
    __tablename__ = "upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)  # in bytes
    num_records = Column(Integer)
    num_errors = Column(Integer, default=0)
    status = Column(String(50))  # success, partial_success, failed
    error_details = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time_seconds = Column(Float)

    # Relationships
    user = relationship("User")


class Dataset(Base):
    """Uploaded dataset lifecycle state."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    uploaded_by = Column(String(255), nullable=False)
    uploaded_role = Column(String(100), nullable=False)
    active = Column(Boolean, default=False, index=True)
    scored_rows = Column(Integer, default=0)
    segment_rows = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SparkJob(Base):
    """Spark pipeline execution tracking."""
    __tablename__ = "spark_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False)
    pipeline_type = Column(String(100))  # full, cleaning, features, aggregation
    status = Column(String(50))  # pending, running, success, failed
    input_path = Column(String(500))
    output_path = Column(String(500))
    error_message = Column(String(2000))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time_seconds = Column(Float)
    records_processed = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelMetric(Base):
    """Model training and evaluation metrics."""
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False)
    model_type = Column(String(100))  # classifier, regressor
    metric_name = Column(String(100))  # accuracy, precision, recall, f1
    metric_value = Column(Float)
    dataset_size = Column(Integer)
    training_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
