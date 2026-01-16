from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./opti_quality.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    image_filename = Column(String)
    prediction = Column(JSON, nullable=True) # Model output
    confidence = Column(Float, default=0.0)
    status = Column(String, default="pending_review") # automated, pending_review, reviewed
    final_prediction = Column(JSON, nullable=True) # Validated output
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String, primary_key=True)
    value = Column(String)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, nullable=True)
    action_type = Column(String) # threshold_change, human_review, model_retrain
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Initialize default config if not exists
    db = SessionLocal()
    try:
        if not db.query(SystemConfig).filter(SystemConfig.key == "confidence_threshold").first():
            db.add(SystemConfig(key="confidence_threshold", value="0.6"))
            db.commit()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
