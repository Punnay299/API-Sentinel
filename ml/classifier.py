import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.pipeline import Pipeline

class ZombieAPIClassifier:
    LABELS = ["active", "deprecated", "orphaned", "zombie", "shadow"]

    def __init__(self):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators    = 300,    # 300 trees in the forest
                max_depth       = 12,     # Prevent overfitting
                min_samples_leaf= 3,      # Each leaf needs ≥3 samples
                max_features    = "sqrt", # √18 ≈ 4 features per split
                class_weight    = "balanced",
                random_state    = 42,
                n_jobs          = -1,     # Use all CPU cores
            ))
        ])
        self.label_encoder = LabelEncoder()
        self.trained = False

    def train(self, X: np.ndarray, y_str: list[str]) -> dict:
        """
        X: shape (n_samples, 18)
        y_str: list of string labels e.g. ["active", "zombie", ...]
        Returns: dict of per-class F1 scores
        """
        y_enc = self.label_encoder.fit_transform(y_str)
        self.pipeline.fit(X, y_enc)
        self.trained = True

        # Compute training accuracy
        y_pred = self.pipeline.predict(X)
        return self._compute_metrics(y_enc, y_pred)

    def predict(self, x: np.ndarray) -> dict:
        """
        x: shape (1, 18) — single API feature vector
        Returns dict with status, confidence, and full probability distribution
        """
        assert self.trained, "Model must be trained before prediction"
        proba  = self.pipeline.predict_proba(x)[0]  # shape (5,)
        idx    = int(np.argmax(proba))
        labels = self.label_encoder.inverse_transform(range(len(proba)))
        return {
            "status":        labels[idx],
            "confidence":    round(float(proba[idx]), 4),
            "probabilities": {labels[i]: round(float(p), 4) for i, p in enumerate(proba)},
        }

    def feature_importances(self) -> dict:
        """Return feature importance scores for explainability."""
        from ml.feature_extractor import FEATURE_COLS
        rf = self.pipeline.named_steps["rf"]
        return dict(zip(FEATURE_COLS, rf.feature_importances_.tolist()))

    def _compute_metrics(self, y_true, y_pred) -> dict:
        from sklearn.metrics import f1_score
        scores = f1_score(y_true, y_pred, average=None)
        labels = self.label_encoder.inverse_transform(range(len(scores)))
        return {label: round(float(s), 4) for label, s in zip(labels, scores)}
