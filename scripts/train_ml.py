"""
CLI Script: Train and Evaluate Supervised Threat Model
Evaluates decision tree classifier, displays accuracy, precision, recall, F1-score, and feature importances.
"""

import sys
import os
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.ml_engine import ml_classifier, DATASET_FILE
from scripts.generate_dataset import generate_dataset


def run_training():
    if not os.path.exists(DATASET_FILE):
        print("[*] Dataset not found. Generating new dataset...")
        generate_dataset(DATASET_FILE, total_records=1500)

    print(f"[*] Training supervised threat classifier from: {DATASET_FILE}")
    ml_classifier.train_from_csv(DATASET_FILE)
    metrics = ml_classifier.metrics

    print("\n=======================================================")
    print("  MODEL TRAINING & EVALUATION REPORT")
    print("=======================================================")
    print(f"  Total Samples     : {metrics.get('total_samples')}")
    print(f"  Test Samples (20%): {metrics.get('test_samples')}")
    print(f"  Accuracy          : {metrics.get('accuracy') * 100:.2f}%")
    print(f"  Precision         : {metrics.get('precision') * 100:.2f}%")
    print(f"  Recall            : {metrics.get('recall') * 100:.2f}%")
    print(f"  F1 Score          : {metrics.get('f1_score') * 100:.2f}%")
    print("-------------------------------------------------------")
    print("  FEATURE IMPORTANCES (Gini Importance):")
    for feat, imp in sorted(metrics.get("feature_importances", {}).items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(imp * 30)
        print(f"    - {feat.ljust(25)}: {imp:0.4f}  {bar}")
    print("-------------------------------------------------------")
    print("  CONFUSION MATRIX (Row: Actual, Col: Predicted):")
    conf = metrics.get("confusion_matrix", {})
    labels = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]
    print(f"    {'':10} " + " ".join(f"{l:>10}" for l in labels))
    for actual in labels:
        row_str = f"    {actual:<10} " + " ".join(f"{conf.get(actual, {}).get(pred, 0):>10}" for pred in labels)
        print(row_str)
    print("=======================================================\n")


if __name__ == "__main__":
    run_training()
