"""JSON Utility Functions for NumPy type conversion"""

import numpy as np
from typing import Any


def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert NumPy types to Python native types for JSON serialization.

    Handles: np.bool_ → bool, np.integer → int, np.floating → float, np.ndarray → list
    """
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return [convert_numpy_types(item) for item in obj.tolist()]
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    if isinstance(obj, tuple):
        return [convert_numpy_types(item) for item in obj]
    return obj
