from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

CaseStage = Literal["queued", "validating", "inspecting", "segmenting", "validating_masks",
                    "reconstructing", "measuring", "reconstructing_and_measuring",
                    "preparing_previews", "validating_artifacts", "complete", "failed"]


class CaseAccepted(BaseModel):
    case_id: str
    status: CaseStage


class CaseStatus(CaseAccepted):
    error: str | None = None
    failed_stage: str | None = None
    history: list[dict] = Field(default_factory=list)


class CaseManifest(CaseStatus):
    model_config = ConfigDict(extra='allow')


class APIConfig(BaseModel):
    engine: str
    task: str
    device: str
    fast_mode: bool
    max_upload_bytes: int
    max_voxels: int
    max_pending: int
    supported_inputs: list[str]
    clinical_validation: bool = False
