import os
import sys
import joblib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

# Purpose: Encapsulate all ML model loading and prediction logic
# (GraphCodeBERT backbone + XGBoost classifier + LR meta-classifier)

# 1. Define project root and model paths
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

MODELS_DIR = os.path.join(PROJECT_ROOT, "model")
CLASSIFIER_PATH_PKL = os.path.join(MODELS_DIR, "classifier.pkl")
LOCAL_BACKBONE_PATH = os.path.join(MODELS_DIR, "graphcodebert-base")
REMOTE_BACKBONE_NAME = "microsoft/graphcodebert-base"

if not os.path.isfile(CLASSIFIER_PATH_PKL):
    raise FileNotFoundError(
        f"Classifier file not found: {CLASSIFIER_PATH_PKL}"
    )


# 2. Predictor class for model loading and inference
class MLPredictor:

    def __init__(self):
        self.CONTEXT_WINDOW = 3  # Expose this for detect.py
        self.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.DEVICE}")

        # Prefer the model bundled with the project. If it is absent,
        # Transformers will download the model from Hugging Face.
        if os.path.isdir(LOCAL_BACKBONE_PATH):
            self.BACKBONE_MODEL_NAME = LOCAL_BACKBONE_PATH
            self.LOCAL_FILES_ONLY = True
            print(f"Using local GraphCodeBERT: {LOCAL_BACKBONE_PATH}")
        else:
            self.BACKBONE_MODEL_NAME = REMOTE_BACKBONE_NAME
            self.LOCAL_FILES_ONLY = False
            print(
                "Local GraphCodeBERT was not found. "
                "Downloading microsoft/graphcodebert-base from Hugging Face."
            )

        try:
            # 1. Load backbone tokenizer
            print(
                f"Loading Backbone Tokenizer: "
                f"{self.BACKBONE_MODEL_NAME}"
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.BACKBONE_MODEL_NAME,
                local_files_only=self.LOCAL_FILES_ONLY,
            )

            # 2. Load backbone model
            print(
                f"Loading Backbone Model: "
                f"{self.BACKBONE_MODEL_NAME}"
            )
            self.backbone_model = AutoModel.from_pretrained(
                self.BACKBONE_MODEL_NAME,
                add_pooling_layer=False,
                local_files_only=self.LOCAL_FILES_ONLY,
            ).to(self.DEVICE)
            self.backbone_model.eval()

            # 3. Load classifier (stacked model)
            print(f"Loading Classifier: {CLASSIFIER_PATH_PKL}")
            self.models_dict, self.meta_model_lr = joblib.load(
                CLASSIFIER_PATH_PKL
            )

        except Exception as e:
            print(
                f"[Predictor] Failed to load ML models: {e}",
                file=sys.stderr,
            )
            raise

    # End-to-end prediction for a single context string
    def predict_one(self, context_text: str) -> int:

        text_to_embed = context_text

        try:
            # Text -> embedding
            inputs = self.tokenizer(
                text_to_embed,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512,
            ).to(self.DEVICE)

            with torch.no_grad():
                outputs = self.backbone_model(**inputs)
                embedding = (
                    outputs.last_hidden_state[:, 0, :].cpu().numpy()
                )

            # Embedding -> base model probabilities
            base_preds = {}
            for model_name, model_obj in self.models_dict.items():
                base_preds[model_name] = model_obj.predict_proba(
                    embedding
                )[:, 1]

            # Stacking -> final prediction
            stacked_preds = np.vstack(
                [base_preds[name] for name in base_preds.keys()]
            ).T

            final_prediction = self.meta_model_lr.predict(stacked_preds)

            return int(final_prediction[0])

        except Exception as e:
            print(
                f"[Predictor] Prediction failed: {e}",
                file=sys.stderr,
            )
            return 0  # Default to Non-Secret
