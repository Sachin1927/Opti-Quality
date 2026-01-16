from ultralytics import YOLO
import os
import shutil
import yaml
from sqlalchemy.orm import Session
from .database import SessionLocal, Inspection, AuditLog, datetime

DATASET_PATH = "data/active_learning"
TRAIN_DIR = os.path.join(DATASET_PATH, "train")

def prepare_dataset():
    """
    Export reviewed inspections into YOLO format.
    """
    db = SessionLocal()
    reviewed = db.query(Inspection).filter(Inspection.status == "reviewed").all()
    
    if len(reviewed) < 5: # Minimum threshold to bother retraining
        db.close()
        return False, "Not enough reviewed data (need at least 5 samples)"

    # Setup directories
    for sub in ["images", "labels"]:
        path = os.path.join(TRAIN_DIR, sub)
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)

    # Class mapping (Assuming 1 class 'defect' for simplicity, or we can extract from predictions)
    # Mapping index: 0 -> 'defect'
    classes = ["defect", "fracture", "stain", "misalignment"] # Example classes
    class_map = {name: i for i, name in enumerate(classes)}

    for item in reviewed:
        # 1. Copy Image
        src_img = os.path.join("data/raw", item.image_filename)
        dest_img = os.path.join(TRAIN_DIR, "images", item.image_filename)
        if os.path.exists(src_img):
            shutil.copy(src_img, dest_img)
        
        # 2. Create Label
        # YOLO format: cls x_center y_center width height (normalized)
        label_filename = item.image_filename.split(".")[0] + ".txt"
        label_path = os.path.join(TRAIN_DIR, "labels", label_filename)
        
        # Use final_prediction if available, else prediction
        data = item.final_prediction if item.final_prediction else item.prediction
        
        with open(label_path, "w") as f:
            if isinstance(data, list):
                for obj in data:
                    cls_name = obj.get("class", "defect").lower()
                    cls_id = class_map.get(cls_name, 0)
                    
                    bbox = obj.get("bbox")
                    if bbox:
                        # Convert [x1, y1, x2, y2] to center_x, center_y, w, h
                        # This part assumes standardized image size or we'd need to fetch actual size
                        # For robustness, we'd open the image and get width/height
                        try:
                            from PIL import Image
                            with Image.open(src_img) as img:
                                img_w, img_h = img.size
                            
                            x1, y1, x2, y2 = bbox
                            w = (x2 - x1) / img_w
                            h = (y2 - y1) / img_h
                            x_center = (x1 + (x2 - x1)/2) / img_w
                            y_center = (y1 + (y2 - y1)/2) / img_h
                            
                            f.write(f"{cls_id} {x_center} {y_center} {w} {h}\n")
                        except Exception as e:
                            print(f"Error processing label for {item.image_filename}: {e}")

    # 3. Create YAML
    dataset_yaml = {
        "path": os.path.abspath(DATASET_PATH),
        "train": "train/images",
        "val": "train/images", # Use train for val as well if dataset is tiny
        "nc": len(classes),
        "names": classes
    }
    
    yaml_path = os.path.join(DATASET_PATH, "dataset.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(dataset_yaml, f)
    
    db.close()
    return True, yaml_path

def train_model():
    """
    Main entry point for retraining.
    """
    db = SessionLocal()
    success, result = prepare_dataset()
    if not success:
        return {"success": False, "message": result}
    
    try:
        # Log start
        db.add(AuditLog(action_type="model_train_start", details="Starting YOLOv11 fine-tuning on human-reviewed data."))
        db.commit()

        # Load current model
        model = YOLO("yolo11n.pt")
        
        # Train for a small number of epochs (fine-tuning)
        # Note: In a real environment, this should happen in a background process
        model.train(data=result, epochs=10, imgsz=640, device='cpu') # Forcing cpu for user safety
        
        # Save the new version
        new_weights = "models/fine_tuned_yolo.pt"
        if not os.path.exists("models"):
            os.makedirs("models")
            
        # Ultralytics saves to 'runs/detect/train/weights/best.pt' usually
        # We find the latest run
        runs_dir = "runs/detect"
        latest_run = sorted(os.listdir(runs_dir))[-1]
        best_pt = os.path.join(runs_dir, latest_run, "weights", "best.pt")
        
        if os.path.exists(best_pt):
            shutil.copy(best_pt, new_weights)
            
            db.add(AuditLog(
                action_type="model_train_complete", 
                details=f"Fine-tuning complete. New weights saved to {new_weights}. Dataset size: {len(os.listdir(os.path.join(TRAIN_DIR, 'images')))} images."
            ))
            db.commit()
            return {"success": True, "message": "Training successful", "weights": new_weights}
        else:
            return {"success": False, "message": "Training finished but weights not found."}

    except Exception as e:
        db.add(AuditLog(action_type="model_train_failed", details=f"Retraining failed: {str(e)}"))
        db.commit()
        return {"success": False, "message": str(e)}
    finally:
        db.close()
