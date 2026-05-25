"""
Conversion prediction model using scikit-learn.
Predicts expected conversions based on ad performance metrics.
"""

from __future__ import annotations

from typing import Any
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import joblib
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class ConversionPredictor:
    """Predictor for campaign conversions."""
    
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.feature_names = ["impressions", "clicks", "spend", "ctr", "cpc"]
    
    def train(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Train the conversion prediction model.
        
        Args:
            records: List of ad performance records with conversions
            
        Returns:
            Training summary
        """
        if len(records) < 5:
            return {"status": "insufficient_data", "records_used": len(records)}
        
        # Extract features and target
        X = []
        y = []
        
        for record in records:
            features = [
                float(record.get("impressions", 0)) or 0,
                float(record.get("clicks", 0)) or 0,
                float(record.get("spend", 0)) or 0,
                float(record.get("ctr", 0)) or 0,
                float(record.get("cpc", 0)) or 0,
            ]
            X.append(features)
            y.append(float(record.get("conversions", 0)) or 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Calculate R² score
        r2_score = self.model.score(X_scaled, y)
        
        # Save model
        model_path = _project_root() / "data" / "curated" / "models"
        model_path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.model, model_path / "conversion_predictor.joblib")
        joblib.dump(self.scaler, model_path / "conversion_scaler.joblib")
        
        return {
            "status": "trained",
            "records_used": len(records),
            "r2_score": round(float(r2_score), 4),
            "model_path": str(model_path / "conversion_predictor.joblib"),
        }
    
    def predict(
        self,
        impressions: float,
        clicks: float,
        spend: float,
        ctr: float,
        cpc: float,
    ) -> dict[str, Any]:
        """
        Predict conversions for given metrics.
        
        Args:
            impressions: Number of impressions
            clicks: Number of clicks
            spend: Total spend
            ctr: Click through rate
            cpc: Cost per click
            
        Returns:
            Prediction result
        """
        try:
            features = np.array([[impressions, clicks, spend, ctr, cpc]])
            X_scaled = self.scaler.transform(features)
            prediction = self.model.predict(X_scaled)[0]
            
            return {
                "predicted_conversions": round(float(max(0, prediction)), 2),
                "confidence": "medium",  # Simple confidence
            }
        except Exception as e:
            return {
                "error": str(e),
                "predicted_conversions": 0.0,
                "confidence": "low",
            }
    
    def load(self) -> bool:
        """Load trained model from disk."""
        try:
            model_path = _project_root() / "data" / "curated" / "models"
            self.model = joblib.load(model_path / "conversion_predictor.joblib")
            self.scaler = joblib.load(model_path / "conversion_scaler.joblib")
            return True
        except Exception:
            return False
