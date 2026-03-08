import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

class ShadowAPIDetector:
    def __init__(self, contamination: float = 0.15):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("iforest", IsolationForest(
                n_estimators  = 200,
                contamination = contamination,   # Expected fraction of outliers
                max_samples   = "auto",          # min(256, n_samples) per tree
                random_state  = 42,
                n_jobs        = -1
            ))
        ])
        self.trained = False

    def train(self, X: np.ndarray):
        """
        Unsupervised training. Learns the normal feature distribution.
        """
        self.pipeline.fit(X)
        self.trained = True

    def predict(self, x: np.ndarray) -> dict:
        """
        Returns anomaly info for a single API.
        """
        assert self.trained, "Shadow detector must be trained before predicting"
        
        # IsolationForest returns -1 for outliers (shadows), 1 for inliers (normal)
        prediction = self.pipeline.predict(x)[0]
        
        # Negative score means more anomalous
        anomaly_score = self.pipeline.score_samples(x)[0]
        
        return {
            "is_shadow": bool(prediction == -1),
            "anomaly_score": round(float(anomaly_score), 4)
        }
