"""Helpers for loading O*NET attribute reference data."""

from pathlib import Path
from typing import Dict, List

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_scale_anchors() -> Dict[str, List[dict]]:
    """Parse Level Scale Anchors.txt into a dict keyed by Element ID.

    Returns a dict like::

        {
            "1.A.1.a.1": [
                {"level": 2, "description": "Understand a television commercial"},
                {"level": 4, "description": "Understand a coach's oral instructions for a sport"},
                {"level": 6, "description": "Understand a lecture on advanced physics"},
            ],
            ...
        }

    Only LV (Level) scale rows are kept.
    """
    anchors: Dict[str, List[dict]] = {}
    path = _DATA_DIR / "Level Scale Anchors.txt"

    with open(path, encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            element_id, _name, scale_id, anchor_value, anchor_desc = parts[:5]
            if scale_id != "LV":
                continue
            anchors.setdefault(element_id, []).append({
                "level": int(anchor_value),
                "description": anchor_desc,
            })

    # Sort each element's anchors by level
    for lst in anchors.values():
        lst.sort(key=lambda x: x["level"])

    return anchors
