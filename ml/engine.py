import asyncio
import numpy as np
import joblib
from pathlib import Path
from functools import partial

from ml.feature_extractor import extract_features
from ml.data_generator import generate_synthetic_data
from ml.classifier import ZombieAPIClassifier
from ml.shadow_detector import ShadowAPIDetector
from ml.heuristic_scorer import HeuristicScorer

class ZombieAPIMLEngine:
    
    def __init__(self):
        self.classifier = ZombieAPIClassifier()
        self.detector = ShadowAPIDetector()
        self.scorer = HeuristicScorer()

    @classmethod
    def load_or_train(cls):
        """
        Fast startup logic. Load from disk to avoid cold starts.
        If missing, trains offline natively and serializes.
        """
        path = Path("models/engine.pkl")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if path.exists():
            # Load pre-trained models from disk instantly
            print("Loading pre-trained ML models from disk...")
            return joblib.load(path)
        else:
            # Train fresh, then save
            print("No saved models found. Bootstrapping new models...")
            engine = cls()
            engine.train()
            joblib.dump(engine, path)
            return engine

    def train(self):
        """
        Synthesizes 5,000 mock records to pre-train both the Random Forest
        and Isolation Forest models before serialization.
        """
        print("Generating 5000 synthetic records for training...")
        dataset = generate_synthetic_data(5000)
        
        X_list = []
        y_labels = []

        for row in dataset:
            features = extract_features(row)
            X_list.append(features)
            y_labels.append(row["meta_label"])

        X = np.array(X_list)

        print("Training Random Forest Classifier...")
        self.classifier.train(X, y_labels)
        
        print("Training Isolation Forest Anomaly Detector...")
        self.detector.train(X)
        print("Training complete.")

    async def analyze_api(self, api_dict: dict) -> dict:
        """
        Full async inference logic running heavy ML models safely 
        off-thread using execution pools.
        """
        loop = asyncio.get_event_loop()
        
        # Pure Python — executes extremely fast synchronously
        features = extract_features(api_dict)
        X = np.array([features])
        
        # Random Forest — CPU-bound, must be in executor to prevent loop lock
        clf_result = await loop.run_in_executor(
            None, partial(self.classifier.predict, X)
        )
        
        # Isolation Forest — CPU-bound, also runs in executor
        shadow_result = await loop.run_in_executor(
            None, partial(self.detector.predict, X)
        )
        
        # Heuristic scorer — pure Python arithmetic, fine on the event loop
        security_result = self.scorer.score(api_dict)
        
        return self._fuse_results(clf_result, shadow_result, security_result, api_dict)
    
    def _fuse_results(self, clf, shadow, security, raw) -> dict:
        """Merges results into one payload."""
        return {
            "api_id": raw.get("id"),
            "endpoint": raw.get("endpoint"),
            "classification": clf,
            "shadow_detection": shadow,
            "security": security
        }
