from typing import Literal
from pydantic import BaseModel

CaseStage = Literal["queued", "inspecting", "segmenting", "reconstructing", "measuring", "complete", "failed"]


class CaseAccepted(BaseModel):
    case_id: str
    status: CaseStage


class CaseStatus(CaseAccepted):
    error: str | None = None
    failed_stage: str | None = None
    history: list[dict] = []
