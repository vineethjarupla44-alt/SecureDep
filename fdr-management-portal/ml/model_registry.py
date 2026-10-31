"""
Model Registry and Serialization Manager for AICTE FDR Portal.

Phase 8: Advanced AI & Machine Learning Intelligence
Provides:
- Safe serialization and loading of Scikit-learn models using Joblib
- Versioning and model governance metadata
- Safe rule-based / statistical fallback when trained artifacts are absent
"""

import os
import json
from datetime import datetime
from pathlib import Path
from ml.preprocessing import FEATURE_NAMES

# Registry directory
REGISTRY_DIR = Path(__file__).resolve().parent / "saved_models"
os.makedirs(REGISTRY_DIR, exist_ok=True)

MODEL_FILENAME = "isolation_forest_v1.0.0.joblib"
METADATA_FILENAME = "isolation_forest_metadata.json"

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False


def save_trained_model(model, metadata, model_name=MODEL_FILENAME):
    """
    Serialize trained model to registry with metadata.

    Args:
        model: Trained estimator or detector instance.
        metadata (dict): Training parameters, sample counts, feature names, and timestamps.
        model_name (str): Storage filename.

    Returns:
        tuple (bool, str): (True, path) or (False, error_reason).
    """
    model_path = REGISTRY_DIR / model_name
    meta_path = REGISTRY_DIR / METADATA_FILENAME

    metadata_payload = dict(metadata)
    metadata_payload["saved_at"] = datetime.utcnow().isoformat()
    metadata_payload["model_filename"] = model_name

    # Save metadata JSON
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata_payload, f, indent=2)
    except Exception as exc:
        return False, f"Failed to save metadata JSON: {exc}"

    # Save model artifact via joblib if available
    if JOBLIB_AVAILABLE and model is not None:
        try:
            joblib.dump(model, model_path)
            return True, str(model_path)
        except Exception as exc:
            return False, f"Failed to serialize model artifact with joblib: {exc}"
    else:
        # Fallback metadata-only persistence
        return True, str(meta_path)


def load_registered_model(model_name=MODEL_FILENAME):
    """
    Load registered model and metadata from storage.

    Returns:
        tuple (model or None, dict metadata): Loaded estimator and metadata dictionary.
    """
    model_path = REGISTRY_DIR / model_name
    meta_path = REGISTRY_DIR / METADATA_FILENAME

    metadata = {
        "status": "UNLOADED",
        "version": "v1.0.0",
        "algorithm": "IsolationForest",
        "joblib_available": JOBLIB_AVAILABLE,
    }

    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                metadata["metadata_loaded"] = True
        except Exception:
            pass

    loaded_model = None
    if JOBLIB_AVAILABLE and model_path.exists():
        try:
            loaded_model = joblib.load(model_path)
            metadata["model_loaded"] = True
            metadata["status"] = "ACTIVE"
        except Exception as exc:
            metadata["status"] = f"LOAD_ERROR: {exc}"
            metadata["model_loaded"] = False
    else:
        metadata["model_loaded"] = False
        metadata["status"] = "STATISTICAL_FALLBACK"

    return loaded_model, metadata


def get_model_health_status():
    """
    Retrieve operational health, availability, and versioning info of ML models.
    """
    _, meta = load_registered_model()
    version_val = meta.get("model_version", meta.get("version", "v1.0.0"))
    return {
        "engine": "IsolationForest" if JOBLIB_AVAILABLE else "StatisticalBenchmark",
        "algorithm": meta.get("algorithm", "IsolationForest"),
        "joblib_support": JOBLIB_AVAILABLE,
        "model_version": version_val,
        "active_version": version_val,
        "status": meta.get("status", "READY"),
        "features": list(FEATURE_NAMES),
        "training_metadata": meta,
        "registry_directory": str(REGISTRY_DIR),
    }
