from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import require_token


router = APIRouter(prefix="/api/dev", tags=["devtools"], dependencies=[Depends(require_token)])


@router.get("/npm.dedupe-plan")
def npm_dedupe_plan(
    project_root: Optional[str] = Query(default=None, description="Path to project root containing package.json"),
) -> dict:
    root = Path(project_root or os.getcwd())
    pkg = root / "package.json"
    if not pkg.exists():
        raise HTTPException(status_code=404, detail=f"package.json not found at {pkg}")
    # We do not execute npm here (security, portability). Return a suggested plan.
    # The client can run these commands manually in their JS workspace.
    commands = [
        "npm ls --all",
        "npm dedupe",
        "npm audit fix --force",
        "npm install",
    ]
    notes = [
        "If using pnpm: pnpm install && pnpm dedupe",
        "If using yarn: yarn install && yarn dedupe (berry) or consider resolutions",
        "Add 'resolutions' in package.json for hard pins if necessary",
    ]
    return {"root": str(root), "commands": commands, "notes": notes}


