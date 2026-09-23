import time
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import RiskPrediction


def get_latest_predictions_map(session: Session, snapshot_ids: list[int] | set[int]) -> dict[int, RiskPrediction]:
    """Bulk-load the latest RiskPrediction for a list of snapshot_ids in a single query."""
    if not snapshot_ids:
        return {}
    id_list = list(snapshot_ids)
    res: dict[int, RiskPrediction] = {}
    chunk_size = 500
    for i in range(0, len(id_list), chunk_size):
        chunk = id_list[i : i + chunk_size]
        preds = session.scalars(
            select(RiskPrediction)
            .where(RiskPrediction.snapshot_id.in_(chunk))
            .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        ).all()
        for p in preds:
            if p.snapshot_id not in res:
                res[p.snapshot_id] = p
    return res


# In-memory fast cache with TTL and explicit invalidation
_MEM_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 60.0


def get_cached(key: str) -> Any | None:
    now = time.time()
    if key in _MEM_CACHE:
        ts, val = _MEM_CACHE[key]
        if now - ts < CACHE_TTL_SECONDS:
            return val
        del _MEM_CACHE[key]
    return None


def set_cached(key: str, val: Any) -> None:
    _MEM_CACHE[key] = (time.time(), val)


def clear_backend_cache(prefix: str | None = None) -> None:
    global _MEM_CACHE
    if prefix is None:
        _MEM_CACHE.clear()
    else:
        _MEM_CACHE = {k: v for k, v in _MEM_CACHE.items() if not k.startswith(prefix)}
