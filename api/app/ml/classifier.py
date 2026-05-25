"""
Campaign classifier using scikit-learn.
Classifies campaigns into high, medium, or low effectiveness categories.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import joblib
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class CampaignClassifier:
    """Classifier for categorizing campaigns by effectiveness."""
    
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=5)
        self.scaler = StandardScaler()
        self.feature_names = ["avg_ctr", "avg_cvr", "avg_cpc", "avg_cpm"]
        self.classes_ = ["low", "medium", "high"]
    
    def train(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Train the classifier on campaign records.
        
        Args:
            records: List of campaign performance records
            
        Returns:
            Training summary
        """
        if len(records) < 10:
            return {"status": "insufficient_data", "records_used": len(records)}
        
        # Extract features
        X = []
        y = []
        
        for record in records:
            features = [
                float(record.get("ctr", 0)) or 0,
                float(record.get("cvr", 0)) or 0,
                float(record.get("cpc", 0)) or 0,
                float(record.get("cpm", 0)) or 0,
            ]
            X.append(features)
            
            # Simple labeling: quality_label from data
            quality = record.get("quality_label", "average").lower()
            if quality == "good":
                y.append(2)  # high
            elif quality == "average":
                y.append(1)  # medium
            else:
                y.append(0)  # low
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Save model
        model_path = _project_root() / "data" / "curated" / "models"
        model_path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.model, model_path / "campaign_classifier.joblib")
        joblib.dump(self.scaler, model_path / "campaign_scaler.joblib")
        
        return {
            "status": "trained",
            "records_used": len(records),
            "model_path": str(model_path / "campaign_classifier.joblib"),
        }
    
    def predict(self, ctr: float, cvr: float, cpc: float, cpm: float) -> dict[str, Any]:
        """
        Predict campaign effectiveness category.
        
        Args:
            ctr: Click Through Rate
            cvr: Conversion Rate
            cpc: Cost Per Click
            cpm: Cost Per Mille
            
        Returns:
            Prediction result with confidence
        """
        try:
            features = np.array([[ctr, cvr, cpc, cpm]])
            X_scaled = self.scaler.transform(features)
            prediction = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]
            
            return {
                "prediction": self.classes_[prediction],
                "confidence": float(max(probabilities)),
                "probabilities": {
                    self.classes_[i]: float(probabilities[i]) 
                    for i in range(len(self.classes_))
                },
            }
        except Exception as e:
            return {
                "error": str(e),
                "prediction": "unknown",
                "confidence": 0.0,
            }
    
    def load(self) -> bool:
        """Load trained model from disk."""
        try:
            model_path = _project_root() / "data" / "curated" / "models"
            self.model = joblib.load(model_path / "campaign_classifier.joblib")
            self.scaler = joblib.load(model_path / "campaign_scaler.joblib")
            return True
        except Exception:
            return False
