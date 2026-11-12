"""
CLI Script: Generate Supervised Threat Classification Dataset
Produces a realistic dataset (data/labeled_threat_dataset.csv) with normal and threat behaviors.
"""

import sys
import os
import csv
import random

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.ml_engine import FEATURE_NAMES, DATASET_FILE


def generate_dataset(output_file: str = DATASET_FILE, total_records: int = 1500):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    rows = []
    random.seed(42)

    # 1. LOW RISK (450 records): Normal authentication, verified account, 0-2 typo failures, trusted location/device
    for _ in range(int(total_records * 0.30)):
        failed = random.choice([0, 0, 1, 2])
        unusual_loc = 0
        unknown_dev = 0
        unusual_t = random.choice([0, 0, 0, 1])
        acc_ver = 1
        cross_loc = 1
        imp_travel = 0
        high_sev = 0
        tamper = 0
        succ_after_fail = 1 if failed > 0 else 0
        rows.append([failed, unusual_loc, unknown_dev, unusual_t, acc_ver, cross_loc, imp_travel, high_sev, tamper, succ_after_fail, "LOW"])

    # 2. MEDIUM RISK (400 records): Repeated password failures (3-7), known device/location, or off-hours access
    for _ in range(int(total_records * 0.27)):
        failed = random.randint(3, 8)
        unusual_loc = random.choice([0, 0, 1])
        unknown_dev = 0
        unusual_t = random.choice([0, 1])
        acc_ver = 1
        cross_loc = 1
        imp_travel = 0
        high_sev = 0
        tamper = 0
        succ_after_fail = 1
        rows.append([failed, unusual_loc, unknown_dev, unusual_t, acc_ver, cross_loc, imp_travel, high_sev, tamper, succ_after_fail, "MEDIUM"])

    # 3. HIGH RISK (350 records): Multiple failed attempts, unknown device, unusual location, 2-region hopping
    for _ in range(int(total_records * 0.23)):
        failed = random.randint(3, 10)
        unusual_loc = 1
        unknown_dev = 1
        unusual_t = random.choice([0, 1])
        acc_ver = random.choice([0, 1])
        cross_loc = random.choice([1, 2])
        imp_travel = random.choice([0, 1])
        high_sev = random.choice([0, 0, 1])
        tamper = 0
        succ_after_fail = 1
        rows.append([failed, unusual_loc, unknown_dev, unusual_t, acc_ver, cross_loc, imp_travel, high_sev, tamper, succ_after_fail, "HIGH"])

    # 4. VERY HIGH RISK (300 records): Multi-region cross-location attack chain (3+ locations), exfiltration, tamper, impossible travel
    for _ in range(int(total_records * 0.20)):
        failed = random.randint(5, 15)
        unusual_loc = 1
        unknown_dev = 1
        unusual_t = random.choice([0, 1])
        acc_ver = random.choice([0, 1])
        cross_loc = random.choice([2, 3, 4])
        imp_travel = random.choice([0, 1, 1])
        high_sev = 1
        tamper = random.choice([0, 1])
        succ_after_fail = 1
        rows.append([failed, unusual_loc, unknown_dev, unusual_t, acc_ver, cross_loc, imp_travel, high_sev, tamper, succ_after_fail, "VERY_HIGH"])

    random.shuffle(rows)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FEATURE_NAMES + ["risk_tag"])
        writer.writerows(rows)

    print(f"[+] Successfully generated {len(rows)} labeled threat records in: {output_file}")


if __name__ == "__main__":
    generate_dataset()
