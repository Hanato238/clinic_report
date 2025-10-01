#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tricho_analyzer.py
- Responsibility: tricho_0..3.json を解析して、結果JSONを out_path に保存

Usage:
  python tricho_analyzer.py /path/to/json_dir /path/to/out_json
"""

import json
import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, List

class TrichoAnalyzer:
    def __init__(self, bins: List[float] = None, labels: List[str] = None):
        self.bins = bins if bins is not None else [0, 30, 60, 90, np.inf]
        self.labels = labels if labels is not None else ["<30 μm", "30-60 μm", "60-90 μm", ">90 μm"]

    def analyze(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        roi = np.array(json_data['roi'])
        ppmm = float(json_data['ppmm'])

        location = json_data['location']
        width_px  = float(np.max(roi[:, 0]) - np.min(roi[:, 0]))
        height_px = float(np.max(roi[:, 1]) - np.min(roi[:, 1]))
        width_mm  = width_px / ppmm
        height_mm = height_px / ppmm
        area_cm2  = (width_mm * height_mm) / 100.0

        num_follicles = len(json_data.get('follicle_units', []))
        hairs = json_data.get('hairs', [])
        num_hairs = len(hairs)

        hair_widths_px = [h['w'] for h in hairs]
        hair_thickness_um = [(w / ppmm) * 1000.0 for w in hair_widths_px]

        if len(hair_thickness_um) > 0:
            ser = pd.Series(hair_thickness_um, dtype="float64")
            classified = pd.cut(ser, bins=self.bins, labels=self.labels, right=False)
            cls_counts = classified.value_counts().sort_index()
        else:
            cls_counts = pd.Series({label: 0 for label in self.labels})

        if area_cm2 > 0:
            density = (cls_counts / area_cm2).round(2)
        else:
            density = pd.Series({label: None for label in self.labels})

        return {
            "location": location,
            "data":{
                "roi": {
                    "width_mm": round(width_mm, 2),
                    "height_mm": round(height_mm, 2),
                    "area_cm2": round(area_cm2, 2)
                },
                "counts": {
                    "follicles": int(num_follicles),
                    "hairs": int(num_hairs)
                },
                "classification": {label: int(cls_counts.get(label, 0)) for label in self.labels},
                "density_per_cm2": {label: (None if density.get(label, None) is None else float(density.get(label))) for label in self.labels}
            }
        }

def analyze_tricho_file(file_path: str, analyzer: TrichoAnalyzer) -> Dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = analyzer.analyze(data)
        result["file"] = os.path.basename(file_path)
        return result
    except FileNotFoundError:
        return {"file": os.path.basename(file_path), "error": "ファイルが見つかりません"}
    except Exception as e:
        return {"file": os.path.basename(file_path), "error": f"解析エラー: {e}"}

def run_on_dir(input_dir: str):
    analyzer = TrichoAnalyzer()
    outputs = []
    for i in range(4):
        file_path = os.path.join(input_dir, f"tricho_{i}.json")
        outputs.append(analyze_tricho_file(file_path, analyzer))
    return outputs

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python tricho_analyzer.py /path/to/json_dir /path/to/out_json")
        sys.exit(1)

    input_dir = sys.argv[1]
    out_json = sys.argv[2]

    results = run_on_dir(input_dir)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Wrote analysis to: {out_json}")
