from ultralytics import YOLO
import os

class DefectDetector:
    def __init__(self, model_path="yolo11n.pt", default_threshold=0.6):
        """
        Initialize the YOLO detector. 
        yolo11n.pt will be downloaded automatically if not found.
        """
        self.model = YOLO(model_path)
        self.default_threshold = default_threshold

    def analyze(self, image_path, threshold=None):
        if threshold is None:
            threshold = self.default_threshold
            
        results = self.model(image_path)[0]
        
        predictions = []
        max_conf = 0
        
        for box in results.boxes:
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            name = results.names[cls]
            xyxy = box.xyxy[0].tolist()
            
            predictions.append({
                "class": name,
                "confidence": conf,
                "bbox": xyxy
            })
            
            if conf > max_conf:
                max_conf = conf

        # Logic for "Uncertainty"
        status = "automated" if max_conf >= threshold else "pending_review"
        
        return {
            "predictions": predictions,
            "max_confidence": max_conf,
            "status": status,
            "used_threshold": threshold
        }

# Singleton instance
detector = DefectDetector()
