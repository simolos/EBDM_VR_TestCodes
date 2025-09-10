
from typing import Any, Dict, Iterable, Optional
import numpy as np
import pandas as pd

def _to_json_scalar(x: Any) -> Any:
    """Convert pandas/NumPy scalars and NaN to JSON-safe Python types."""
    # NaN/NaT -> None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    # NumPy scalar -> Python scalar
    if isinstance(x, np.generic):
        return x.item()
    # Primitive types are already fine
    if isinstance(x, (bool, int, float, str)) or x is None:
        return x
    # Fallback (shouldn't happen for trials row): stringify
    return str(x)

def trial_row_payload(
    trials: pd.DataFrame,
    i: int,
    include: Optional[Iterable[str]] = None,  # keep None to send ALL columns
    exclude: Optional[Iterable[str]] = None,  # or exclude a few if needed
    drop_none: bool = False,                  # keep None if you want explicit "unknown"
) -> Dict[str, Any]:
    """Build a JSON-safe dict from trials.iloc[i] (only trial info)."""
    row = trials.iloc[i]
    cols = list(row.index)

    if include is not None:
        cols = [c for c in cols if c in include]
    if exclude is not None:
        cols = [c for c in cols if c not in exclude]

    payload: Dict[str, Any] = {}
    for col in cols:
        val = _to_json_scalar(row[col])
        if (val is None) and drop_none:
            continue
        payload[col] = val

    # Ensure a proper int for "trial" if present
    if "trial" in payload and payload["trial"] is not None:
        try:
            payload["trial"] = int(payload["trial"])
        except Exception:
            pass

    return payload
