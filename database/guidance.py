import csv
from pathlib import Path


GUIDANCE_PATH = Path(__file__).resolve().parent / "dataset" / "disease_guidance.csv"


def load_guidance():
    with GUIDANCE_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return {row["disease_id"]: row for row in csv.DictReader(file)}
