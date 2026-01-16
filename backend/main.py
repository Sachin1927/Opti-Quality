from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import shutil
import os
import uuid
from typing import List

from .database import engine, init_db, get_db, Inspection, SystemConfig, AuditLog
from .detector import detector
from .trainer import train_model

# Create tables
init_db()

app = FastAPI(title="Opti-Quality: HITL Inspection System")

# Ensure directories exist
UPLOAD_DIR = "data/raw"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

@app.get("/")
async def root():
    return {"message": "Opti-Quality API is active."}

@app.post("/upload/")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Fetch current threshold
    threshold_config = db.query(SystemConfig).filter(SystemConfig.key == "confidence_threshold").first()
    current_threshold = float(threshold_config.value) if threshold_config else 0.6
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Run Model Inference
    analysis = detector.analyze(file_path, threshold=current_threshold)
    
    # Save to Database
    new_inspection = Inspection(
        image_filename=filename,
        prediction=analysis["predictions"],
        confidence=analysis["max_confidence"],
        status=analysis["status"]
    )
    db.add(new_inspection)
    db.commit()
    db.refresh(new_inspection)
    
    return {
        "id": new_inspection.id,
        "filename": filename,
        "status": analysis["status"],
        "confidence": analysis["max_confidence"],
        "threshold_used": current_threshold
    }

@app.get("/inspections/", response_model=None)
async def get_inspections(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Inspection)
    if status:
        query = query.filter(Inspection.status == status)
    return query.order_by(Inspection.created_at.desc()).all()

@app.post("/review/{inspection_id}")
async def submit_review(inspection_id: int, review_data: dict, db: Session = Depends(get_db)):
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    
    old_status = inspection.status
    inspection.final_prediction = review_data.get("final_prediction")
    inspection.status = "reviewed"
    
    # Add Audit Log
    audit = AuditLog(
        inspection_id=inspection_id,
        action_type="human_review",
        details=f"Human reviewer updated status from {old_status} to reviewed. Notes: {review_data.get('final_prediction', {}).get('notes', 'None')}"
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Review submitted successfully"}

@app.get("/stats/")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(Inspection).count()
    automated = db.query(Inspection).filter(Inspection.status == "automated").count()
    pending = db.query(Inspection).filter(Inspection.status == "pending_review").count()
    reviewed = db.query(Inspection).filter(Inspection.status == "reviewed").count()
    
    return {
        "total": total,
        "automated": automated,
        "pending": pending,
        "reviewed": reviewed
    }

@app.get("/config/{key}")
async def get_config(key: str, db: Session = Depends(get_db)):
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"key": key, "value": config.value}

@app.post("/config/")
async def set_config(config_data: dict, db: Session = Depends(get_db)):
    key = config_data.get("key")
    value = str(config_data.get("value"))
    
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config:
        old_value = config.value
        config.value = value
    else:
        old_value = "None"
        config = SystemConfig(key=key, value=value)
        db.add(config)
    
    # Audit trail for config change
    audit = AuditLog(
        action_type="config_change",
        details=f"Config '{key}' changed from {old_value} to {value}"
    )
    db.add(audit)
    db.commit()
    return {"message": f"Config {key} updated"}

@app.get("/drift/")
async def detect_drift(db: Session = Depends(get_db)):
    # Fetch recent inspections (last 100)
    inspections = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(100).all()
    
    if len(inspections) < 40:
        return {
            "drift_detected": False,
            "message": "Insufficient data for drift analysis (need at least 40 scans)",
            "recent_avg": 0,
            "baseline_avg": 0
        }
    
    # Split into Recent (top 20) and Baseline (rest)
    recent = inspections[:20]
    baseline = inspections[20:]
    
    recent_avg = sum(item.confidence for item in recent) / len(recent)
    baseline_avg = sum(item.confidence for item in baseline) / len(baseline)
    
    # If confidence drops by more than 15% relative to baseline
    drift_score = baseline_avg - recent_avg
    is_drift = drift_score > 0.15
    
    # Store in Audit Log if drift detected and not recently logged
    if is_drift:
        last_drift_log = db.query(AuditLog).filter(AuditLog.action_type == "drift_alert").order_by(AuditLog.timestamp.desc()).first()
        # Log at most once per hour
        if not last_drift_log or (datetime.datetime.utcnow() - last_drift_log.timestamp).total_seconds() > 3600:
            audit = AuditLog(
                action_type="drift_alert",
                details=f"CRITICAL: Performance drift detected. Confidence dropped from {baseline_avg:.2f} (baseline) to {recent_avg:.2f} (recent)."
            )
            db.add(audit)
            db.commit()

    return {
        "drift_detected": bool(is_drift),
        "drift_score": float(drift_score),
        "recent_avg": float(recent_avg),
        "baseline_avg": float(baseline_avg),
        "count": len(inspections)
    }

@app.post("/retrain/")
async def trigger_retrain():
    # In a production app, this should be an async task (Celery/RQ)
    result = train_model()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
