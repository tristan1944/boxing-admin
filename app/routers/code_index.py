from __future__ import annotations

import hashlib
from pathlib import Path
import fnmatch
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import require_token
from ..embeddings import get_embedding_provider, cosine_similarity
from ..database import SessionLocal
from ..models import CodeEmbedding


router = APIRouter(prefix="/api/code", tags=["code-embeddings"], dependencies=[Depends(require_token)])


DEFAULT_IGNORES = [
    "**/node_modules/**",
    "**/.git/**",
    "**/.venv/**",
    "**/dist/**",
    "**/build/**",
    "**/.next/**",
]


def _is_ignored(path: Path, ignore_patterns: list[str]) -> bool:
    s = str(path)
    for pat in ignore_patterns:
        if fnmatch.fnmatch(s, pat):
            return True
    return False


def _iter_files(root: Path, include_exts: set[str], ignore_patterns: list[str]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if _is_ignored(p, ignore_patterns):
            continue
        if p.is_file() and p.suffix in include_exts:
            yield p


def _read_file(path: Path, max_bytes: int = 20000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data
    except Exception:
        return ""


@router.post("/backfill")
def code_backfill(
    root_dir: Optional[str] = Query(default=None, description="Root directory to index; defaults to CWD"),
    exts: Optional[str] = Query(default=".py,.ts,.tsx,.js,.json,.md"),
    ignores: Optional[str] = Query(default=None, description="Comma-separated glob patterns to ignore"),
    persist: bool = False,
) -> dict:
    # Stateless by default; persistence is opt-in
    provider = get_embedding_provider()
    root = Path(root_dir or ".").resolve()
    include_exts = set((exts or "").split(","))
    ignore_patterns = DEFAULT_IGNORES + ([p.strip() for p in (ignores or "").split(",") if p.strip()]
        if ignores else [])
    files = list(_iter_files(root, include_exts, ignore_patterns))

    texts: List[str] = []
    meta: List[dict] = []
    seen_keys: set[tuple[str, int, str]] = set()
    for f in files:
        content = _read_file(f)
        if not content:
            continue
        rel_path = str(f.relative_to(root))
        text_hash = hashlib.sha256(content.encode()).hexdigest()
        key = (rel_path, 0, text_hash)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        texts.append(content)
        meta.append({"path": rel_path, "sha256": hashlib.sha256(content.encode()).hexdigest()})

    vectors = provider.embed_texts(texts) if texts else []
    if persist and vectors:
        db = SessionLocal()
        try:
            # Preload existing keys to make inserts idempotent
            existing = set(
                db.query(CodeEmbedding.path, CodeEmbedding.chunk_idx, CodeEmbedding.text_hash).all()
            )
            for m, vec, content in zip(meta, vectors, texts):
                rel_path = m["path"]
                chunk_idx = 0
                text_hash = hashlib.sha256(content.encode()).hexdigest()
                key = (rel_path, chunk_idx, text_hash)
                if key in existing:
                    continue
                db.add(
                    CodeEmbedding(
                        path=rel_path,
                        file_sha256=m["sha256"],
                        lang=Path(rel_path).suffix.lstrip("."),
                        chunk_idx=chunk_idx,
                        text_hash=text_hash,
                        vector=vec,
                    )
                )
            db.commit()
        finally:
            db.close()
    return {"count": len(vectors), "meta": meta, "vectors": vectors, "persisted": bool(persist)}


@router.post("/search")
def code_search(
    q: str,
    root_dir: Optional[str] = Query(default=None),
    exts: Optional[str] = Query(default=".py,.ts,.tsx,.js,.json,.md"),
    ignores: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    use_persisted: bool = Query(default=False, description="Search persisted code embeddings if true"),
) -> dict:
    provider = get_embedding_provider()
    q_vec = provider.embed_texts([q])[0]
    if use_persisted:
        db = SessionLocal()
        try:
            rows = db.query(CodeEmbedding).all()
            scored = []
            for r in rows:
                if not r.vector:
                    continue
                score = cosine_similarity(q_vec, r.vector)
                scored.append((score, {"path": r.path}))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:limit]
            return {"items": [{"score": round(s, 6), **m} for s, m in top], "total": len(scored), "source": "persisted"}
        finally:
            db.close()
    # Stateless fallback
    backfill = code_backfill(root_dir=root_dir, exts=exts, ignores=ignores, persist=False)
    scored = []
    for meta, vec in zip(backfill["meta"], backfill["vectors"]):
        score = cosine_similarity(q_vec, vec)
        scored.append((score, meta))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    return {"items": [{"score": round(s, 6), **m} for s, m in top], "total": len(scored), "source": "ephemeral"}


