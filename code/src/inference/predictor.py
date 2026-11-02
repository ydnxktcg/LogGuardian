import os
import sys
import joblib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

# Purpose: Encapsulate all ML model loading and prediction logic
# (Backbone + XGBoost classifier)

# 1. Define project root and model paths
try:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    MODELS_DIR = os.path.join(PROJECT_ROOT, 'model')
    CLASSIFIER_PATH_PKL = os.path.join(MODELS_DIR, 'classifier.pkl')

    if not os.path.exists(CLASSIFIER_PATH_PKL):
        raise FileNotFoundError(f"Model file not found: {CLASSIFIER_PATH_PKL}")

except FileNotFoundError:
    sys.exit(1)


# 2. Predictor class for model loading and inference
class MLPredictor:

    def __init__(self):
        self.BACKBONE_MODEL_NAME = "microsoft/graphcodebert-base"
        self.CONTEXT_WINDOW = 3   # Expose this for detect.py
        self.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.DEVICE}")

        try:
            # 1. Load backbone tokenizer
            print(f"Loading Backbone Tokenizer: {self.BACKBONE_MODEL_NAME}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.BACKBONE_MODEL_NAME)

            # 2. Load backbone model
            print(f"Loading Backbone Model: {self.BACKBONE_MODEL_NAME}")
            self.backbone_model = AutoModel.from_pretrained(
                self.BACKBONE_MODEL_NAME, add_pooling_layer=False
            ).to(self.DEVICE)
            self.backbone_model.eval()

            # 3. Load classifier (stacked model)
            print(f"Loading Classifier: {CLASSIFIER_PATH_PKL}")
            self.models_dict, self.meta_model_lr = joblib.load(CLASSIFIER_PATH_PKL)

        except Exception as e:
            print(f"❌ [Predictor] Failed to load ML models: {e}", file=sys.stderr)
            raise e

    # End-to-end prediction for a single context string
    def predict_one(self, context_text: str) -> int:

        text_to_embed = context_text

        try:
            # Text → embedding
            inputs = self.tokenizer(
                text_to_embed, return_tensors="pt",
                truncation=True, padding=True, max_length=512
            ).to(self.DEVICE)

            with torch.no_grad():
                outputs = self.backbone_model(**inputs)
                embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()

            # Embedding → base model probabilities
            base_preds = {}
            for model_name, model_obj in self.models_dict.items():
                base_preds[model_name] = model_obj.predict_proba(embedding)[:, 1]

            # Stacking → final prediction
            stacked_preds = np.vstack(
                [base_preds[name] for name in base_preds.keys()]
            ).T

            final_prediction = self.meta_model_lr.predict(stacked_preds)

            return int(final_prediction[0])

        except Exception:
            return 0  # Default to Non-Secret
