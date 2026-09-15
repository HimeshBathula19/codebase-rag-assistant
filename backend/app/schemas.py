from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SUPPORTED_TOP_K = (3, 5, 8, 12)
ANALYSIS_MODES = ("quick", "standard", "deep")
SearchMode = Literal["keyword", "semantic", "hybrid"]


class RepositoryCreate(BaseModel):
    url: str = Field(..., min_length=8, max_length=500)
    github_token: str | None = Field(default=None, max_length=200)
    branch: str | None = Field(default=None, max_length=200)
    analysis_mode: str = "standard"
    top_k: int = 8
    semantic_weight: float | None = None
    keyword_weight: float | None = None

    @field_validator("analysis_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        mode = value.strip().lower()
        if mode not in ANALYSIS_MODES:
            raise ValueError(f"analysis_mode must be one of {ANALYSIS_MODES}")
        return mode

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int) -> int:
        if value not in SUPPORTED_TOP_K:
            raise ValueError(f"top_k must be one of {SUPPORTED_TOP_K}")
        return value


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int | None = None

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in SUPPORTED_TOP_K:
            raise ValueError(f"top_k must be one of {SUPPORTED_TOP_K}")
        return value


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    mode: SearchMode = "hybrid"
    top_k: int | None = None

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in SUPPORTED_TOP_K:
            raise ValueError(f"top_k must be one of {SUPPORTED_TOP_K}")
        return value


class EvidenceItem(BaseModel):
    file: str
    symbol: str | None = None
    start_line: int
    end_line: int
    snippet: str | None = None
    score: float | None = None
    language: str | None = None
    symbol_type: str | None = None


class AskResponse(BaseModel):
    answer: str
    confidence: float
    how_it_works: list[str]
    execution_flow: list[dict[str, Any]]
    evidence: list[EvidenceItem]
    related_files: list[str]
    grounded: bool
    insufficient_evidence: bool


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict[str, Any] | None = None
