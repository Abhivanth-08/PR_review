"""
Pydantic models for PR Review Agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    READABILITY = "readability"
    BEST_PRACTICES = "best_practices"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class FileChange(BaseModel):
    filename: str
    additions: int
    deletions: int
    patch: str
    status: str  # added, modified, deleted


class PRMetadata(BaseModel):
    pr_number: int
    title: str
    description: Optional[str]
    author: str
    branch: str
    files_changed: int
    additions: int
    deletions: int


class ReviewIssue(BaseModel):
    category: IssueCategory
    severity: Severity
    line_number: Optional[int] = None
    filename: str
    code_snippet: str
    issue_description: str
    recommendation: str
    reasoning: str


class LogicAnalysisOutput(BaseModel):
    issues: List[ReviewIssue] = Field(default_factory=list)
    potential_bugs: List[str] = Field(default_factory=list)
    edge_cases_missing: List[str] = Field(default_factory=list)


class SecurityAnalysisOutput(BaseModel):
    vulnerabilities: List[ReviewIssue] = Field(default_factory=list)
    security_score: int = Field(ge=0, le=100)
    critical_issues: List[str] = Field(default_factory=list)


class PerformanceAnalysisOutput(BaseModel):
    bottlenecks: List[ReviewIssue] = Field(default_factory=list)
    optimization_suggestions: List[str] = Field(default_factory=list)
    complexity_warnings: List[str] = Field(default_factory=list)


class ReadabilityAnalysisOutput(BaseModel):
    style_issues: List[ReviewIssue] = Field(default_factory=list)
    naming_suggestions: List[str] = Field(default_factory=list)
    documentation_needed: List[str] = Field(default_factory=list)
    readability_score: int = Field(ge=0, le=100)


class TestingAnalysisOutput(BaseModel):
    missing_tests: List[str] = Field(default_factory=list)
    test_coverage_concerns: List[str] = Field(default_factory=list)
    test_quality_issues: List[ReviewIssue] = Field(default_factory=list)


class AggregatedReview(BaseModel):
    overall_assessment: str
    approval_status: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    critical_blockers: List[ReviewIssue]
    all_issues: List[ReviewIssue]
    strengths: List[str]
    summary_by_category: Dict[str, int]
    priority_actions: List[str]


class PRReviewRequest(BaseModel):
    github_url: Optional[str] = None
    diff_content: Optional[str] = None
    pr_metadata: Optional[Dict] = None

    class Config:
        # Allow extra fields to be ignored (works for both Pydantic v1 and v2)
        extra = "ignore"


class PRReviewResponse(BaseModel):
    pr_metadata: Optional[PRMetadata]
    review: AggregatedReview
    agent_analyses: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float