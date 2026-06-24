"""`/digests` router — read the stored decision-oriented briefings (M7).

Read-only: digests are *generated* by the CLI (`python -m app.cli digest`), which wires the LLM
provider, embedder, and stores. The dashboard reads them. `GET /digests` lists newest-first;
`GET /digests/{id}` returns the rendered briefing plus the Events it drew from (each item keeps its
source link via the digest body).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import session_dep
from app.models import Digest
from app.schemas.api import DigestOut, DigestSummaryOut

router = APIRouter(tags=["digests"])


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


@router.get("/digests", response_model=list[DigestSummaryOut])
def list_digests(session: Session = Depends(session_dep)) -> list[DigestSummaryOut]:
    """List stored digests, newest first."""
    rows = session.exec(select(Digest).order_by(Digest.generated_at.desc())).all()
    return [
        DigestSummaryOut(
            id=d.id,
            period_start=_iso(d.period_start),
            period_end=_iso(d.period_end),
            generated_at=_iso(d.generated_at),
            method=d.method,
            item_count=d.item_count,
            noise_count=d.noise_count,
            graphrag=d.graphrag,
        )
        for d in rows
    ]


@router.get("/digests/{digest_id}", response_model=DigestOut)
def get_digest(digest_id: int, session: Session = Depends(session_dep)) -> DigestOut:
    """Return one stored digest in full."""
    d = session.get(Digest, digest_id)
    if d is None:
        raise HTTPException(status_code=404, detail=f"no such digest {digest_id}")
    return DigestOut(
        id=d.id,
        period_start=_iso(d.period_start),
        period_end=_iso(d.period_end),
        generated_at=_iso(d.generated_at),
        method=d.method,
        item_count=d.item_count,
        noise_count=d.noise_count,
        graphrag=d.graphrag,
        content_md=d.content_md,
        event_ids=list(d.event_ids or []),
    )
