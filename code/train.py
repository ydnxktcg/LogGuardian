import os
import json
import numpy as np
import xgboost as xgb
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from transformers import AutoTokenizer, AutoModel
import torch
from tqdm import tqdm
import argparse
import joblib
import random

# Configuration
DATA_DIR = 'data'
CLASS_NAMES = ['Non-Secret', 'Secret']
POSITIVE_LABEL = 'Secret'
DEFAULT_BACKBONE = "microsoft/graphcodebert-base"
MODEL_SAVE_PATH = 'model/classifier.pkl'
CACHE_DIR = 'model/cache_embedding'


# ============================================
# set_seed function
# ============================================
def set_seed(seed):
    """
    Set all relevant random seeds to ensure reproducibility.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    print(f"🌱 Random seed set to: {seed}")


# ============================================
# Step 1: Load JSON data
# ============================================
def load_json_data(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return [], []
    texts, labels = [], []
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            context = item.get('context')
            label = item.get('label')
            if context is not None and label is not None:
                texts.append(context)
                labels.append(1 if label == POSITIVE_LABEL else 0)
    return texts, labels


# ============================================
# Step 2: Text → Embeddings
# ============================================
def get_features(text_list, model_name, split_name, batch_size=32):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{split_name}_embeddings.npy")

    # Enable cache loading (if exists)
    if os.path.exists(cache_path):
        print(f"⚡ Loading cached embeddings from {cache_path}")
        return np.load(cache_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"🚀 Extracting features using {model_name} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()

    all_embeddings = []
    for i in tqdm(range(0, len(text_list), batch_size), desc=f"{split_name} feature extraction"):
        batch_texts = text_list[i:i + batch_size]
        inputs = tokenizer(batch_texts, return_tensors="pt", truncation=True,
                           padding=True, max_length=512).to(device)
        with torch.no_grad():
            outputs = model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            all_embeddings.extend(embeddings)

    all_embeddings = np.array(all_embeddings)
    np.save(cache_path, all_embeddings)
    return all_embeddings


# ============================================
# Step 3: Main Training Logic
# ============================================
def train_and_evaluate_models(X_train, y_train, X_val, y_val, X_test, y_test, seed):
    # 1. Initialize base model (XGBoost)
    models = {
        'xgb': xgb.XGBClassifier(
            objective='binary:logistic',
            scale_pos_weight=3,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            n_estimators=1000,
            learning_rate=0.01,
            gamma=1.5,
            reg_lambda=3.0,
            reg_alpha=1.5,
            min_child_weight=5,
            early_stopping_rounds=100,
            # Pass the main seed to XGBoost for enhanced reproducibility
            seed=seed
        ),
    }

    X_train = np.array(X_train)
    X_val = np.array(X_val)
    X_test = np.array(X_test)

    # 2. Train the base model
    for model_name, model in models.items():
        eval_set = [(X_val, y_val)]
        model.fit(X_train, y_train, eval_set=eval_set, verbose=True)
        print(f"✅ {model_name} trained successfully!")

    # 3. Make predictions using the base model on the validation set
    model_preds = {}
    for model_name, model in models.items():
        model_preds[model_name] = model.predict_proba(X_val)[:, 1]

    # 4. Stack the predictions
    stacked_preds = np.vstack([model_preds[model_name] for model_name in models.keys()]).T

    # 5. Define and train the meta-model (Logistic Regression)
    print("\n--- Training the meta-model (Logistic Regression) ---")

    # Use the provided best parameters
    best_params = {
        'C': 0.1,
        'penalty': 'l2',
        'solver': 'liblinear',
        'class_weight': 'balanced',
        'max_iter': 1000,
        'random_state': seed  # Pass the main seed to LR
    }

    meta_model = LogisticRegression(**best_params)
    meta_model.fit(stacked_preds, y_val)
    print("✅ Logistic Regression (Meta-Model) trained successfully!")

    # 6. Make predictions on the test set
    test_preds = {}
    for model_name, model in models.items():
        test_preds[model_name] = model.predict_proba(X_test)[:, 1]

    stacked_test_preds = np.vstack([test_preds[model_name] for model_name in models.keys()]).T
    final_preds = meta_model.predict(stacked_test_preds)
    final_probs = meta_model.predict_proba(stacked_test_preds)[:, 1]

    # --- Calculate and output evaluation metrics ---
    acc = metrics.accuracy_score(y_test, final_preds)
    f1 = metrics.f1_score(y_test, final_preds, average='macro')
    auc = metrics.roc_auc_score(y_test, final_probs)
    f2 = metrics.fbeta_score(y_test, final_preds, beta=2, average='macro')
    mcc = metrics.matthews_corrcoef(y_test, final_preds)

    # Output confusion matrix
    cm = metrics.confusion_matrix(y_test, final_preds)

    print("\n" + "=" * 30)
    print(" Confusion Matrix ")
    print("=" * 30)
    print("True Label:")
    print(f"       {CLASS_NAMES[0]} | {CLASS_NAMES[1]} (Predicted Label)")
    print(f"{CLASS_NAMES[0]} | {cm[0][0]:<10} {cm[0][1]:<10}")
    print(f"{CLASS_NAMES[1]} | {cm[1][0]:<10} {cm[1][1]:<10}")
    print("-" * 30)
    print(f"True Negatives (TN): {cm[0][0]} | False Positives (FP): {cm[0][1]}")
    print(f"False Negatives (FN): {cm[1][0]} | True Positives (TP): {cm[1][1]}")
    print("-" * 30 + "\n")

    # Print all metrics
    print(metrics.classification_report(y_test, final_preds, target_names=CLASS_NAMES, digits=4))
    print(f"Accuracy: {acc:.4f}")
    print(f"F1 (macro): {f1:.4f}")
    print(f"F2 (macro): {f2:.4f}")
    print(f"MCC: {mcc:.4f}")
    print(f"AUC: {auc:.4f}")

    return models, meta_model, acc, f1, auc, f2, mcc


# ============================================
# Step 4: Main
# ============================================
def main(backbone_model, seed):
    set_seed(seed)

    print("\n=== ⏳ Step 1: Loading pre-split data ===")
    train_path = os.path.join(DATA_DIR, "Train.json")
    val_path = os.path.join(DATA_DIR, "Val.json")
    test_path = os.path.join(DATA_DIR, "Test.json")

    X_train_texts, y_train = load_json_data(train_path)
    X_val_texts, y_val = load_json_data(val_path)
    X_test_texts, y_test = load_json_data(test_path)

    if len(X_train_texts) == 0:
        print("❌ Error: Training data is empty, exiting.")
        return

    print(f"  > Train: {len(X_train_texts)}")
    print(f"  > Validation: {len(X_val_texts)}")
    print(f"  > Test: {len(X_test_texts)}")

    print("\n=== ⚙️ Step 2: Extracting / Loading Features ===")
    X_train = get_features(X_train_texts, backbone_model, "train")
    X_val = get_features(X_val_texts, backbone_model, "val")
    X_test = get_features(X_test_texts, backbone_model, "test")

    print("\n=== 🌲 Step 3: Training and Evaluating Models (Stacking with Custom LR Params) ===")
    models, meta_model, acc, f1, auc, f2, mcc = train_and_evaluate_models(
        X_train, y_train, X_val, y_val, X_test, y_test, seed
    )

    # --- Step 5: Save model ---
    model_dir = 'model'
    os.makedirs(model_dir, exist_ok=True)

    final_model_path = MODEL_SAVE_PATH
    joblib.dump((models, meta_model), final_model_path)

    print(f"\n💾 Model saved to: {final_model_path}")


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train a binary classifier for secret detection.")
    parser.add_argument("--backbone", type=str, default=DEFAULT_BACKBONE)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    main(args.backbone, args.seed)
