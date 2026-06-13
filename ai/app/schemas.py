from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


IntentName = Literal[
    "auto",
    "profile",
    "idea",
    "policy",
    "legal",
    "finance",
    "simulation",
    "operation",
    "marketing",
    "commercial_area",
    "plan",
    "collaboration",
    "roadmap",
]


class StartupProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    major: str | None = None
    experiences: list[str] = Field(default_factory=list)
    region: str | None = None
    budget_krw: int | None = None
    available_hours_per_week: int | None = Field(default=None, ge=0, le=168)
    target_income_krw: int | None = Field(default=None, ge=0)
    has_team: bool | None = None
    owned_assets: list[str] = Field(default_factory=list)
    customer_network: list[str] = Field(default_factory=list)
    confirmed_absent_fields: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_channels: list[str] = Field(default_factory=list)
    preferred_business_types: list[str] = Field(default_factory=list)
    avoid_business_types: list[str] = Field(default_factory=list)
    startup_stage: str = "예비창업"
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    memo: str | None = None


class Source(BaseModel):
    title: str
    url: str | None = None
    note: str | None = None


class AgentResponse(BaseModel):
    intent: str
    agent: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    message: str
    profile: StartupProfile = Field(default_factory=StartupProfile)
    intent: IntentName = "auto"
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class LLMChatRequest(BaseModel):
    message: str
    system_prompt: str = "You are a helpful Korean startup assistant. Answer concisely."
    temperature: float = Field(default=0.3, ge=0, le=2)


class ProfileRequest(BaseModel):
    profile: StartupProfile
    question: str | None = None
    use_llm_extraction: bool = True


class IdeaRequest(BaseModel):
    profile: StartupProfile
    count: int = Field(default=3, ge=1, le=5)
    guidance: str | None = None


class PolicyRequest(BaseModel):
    profile: StartupProfile
    query: str | None = None
    limit: int = Field(default=5, ge=1, le=10)
    context: dict[str, Any] = Field(default_factory=dict)


class PlanRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    target: str = "창업 지원사업"
    idea_name: str | None = None
    support_program: dict[str, Any] = Field(default_factory=dict)
    focused_section: dict[str, Any] = Field(default_factory=dict)
    goal: str = "ALIGN_SUPPORT"
    context: dict[str, Any] = Field(default_factory=dict)


class LegalRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    query: str
    limit: int = Field(default=5, ge=1, le=10)
    domains: list[str] = Field(default_factory=list)


class FinanceAssumption(BaseModel):
    item_name: str = "소자본 창업 아이템"
    business_type: str = "auto"
    sales_channel: str = "auto"
    unit_label: str = "건"
    rent_krw_per_month: int = 2_000_000
    equipment_krw: int = 2_000_000
    initial_inventory_krw: int = 1_000_000
    marketing_krw_per_month: int = 500_000
    labor_cost_krw_per_month: int = 0
    other_fixed_cost_krw_per_month: int = 500_000
    price_per_unit_krw: int = 8_000
    expected_daily_customers: int = 40
    variable_cost_rate: float = Field(default=0.35, ge=0, le=1)
    platform_fee_rate: float = Field(default=0.0, ge=0, le=1)
    payment_fee_rate: float = Field(default=0.03, ge=0, le=1)
    tax_buffer_rate: float = Field(default=0.10, ge=0, le=1)
    packaging_cost_krw_per_unit: int = 0
    delivery_cost_krw_per_unit: int = 0
    operating_days_per_month: int = Field(default=26, ge=1, le=31)
    cash_reserve_months: int = Field(default=1, ge=0, le=12)
    startup_buffer_rate: float = Field(default=0.10, ge=0, le=1)


class FinanceRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    assumption: FinanceAssumption = Field(default_factory=FinanceAssumption)


class SimulationStartRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    item_name: str = "로컬 SNS 콘텐츠 스튜디오"
    business_type: Literal["cafe", "commerce", "content", "popup", "service"] = "content"
    difficulty: Literal["easy", "normal", "hard"] = "normal"
    seed: int | None = None


class SimulationChoiceRequest(BaseModel):
    session_id: str
    choice_id: str


class OperationMetric(BaseModel):
    name: str
    value: float
    unit: str | None = None
    memo: str | None = None


class OperationRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    business_name: str = "테스트 매장"
    period: str | None = None
    notes: str | None = None
    daily_sales_krw: list[int] = Field(default_factory=list)
    weekly_sales_krw: list[int] = Field(default_factory=list)
    monthly_sales_krw: int | None = Field(default=None, ge=0)
    orders: int | None = Field(default=None, ge=0)
    ad_spend_krw: int | None = Field(default=None, ge=0)
    material_cost_krw: int | None = Field(default=None, ge=0)
    labor_cost_krw: int | None = Field(default=None, ge=0)
    fixed_cost_krw: int | None = Field(default=None, ge=0)
    impressions: int | None = Field(default=None, ge=0)
    clicks: int | None = Field(default=None, ge=0)
    conversion_rate: float | None = Field(default=None, ge=0, le=1)
    inventory_notes: list[str] = Field(default_factory=list)
    stockout_items: list[str] = Field(default_factory=list)
    slow_moving_items: list[str] = Field(default_factory=list)
    customer_feedback: list[str] = Field(default_factory=list)
    review_keywords: list[str] = Field(default_factory=list)
    complaints: list[str] = Field(default_factory=list)
    channel_notes: list[str] = Field(default_factory=list)
    product_sales: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[OperationMetric] = Field(default_factory=list)


class CommercialAreaRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    query: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

class MarketingRequest(BaseModel):
    profile: StartupProfile = Field(default_factory=StartupProfile)
    product_name: str
    event_date: str | None = None
    target_customer: str | None = None
    place: str | None = None
    brand_tone: str = "친근하고 실행력 있는"
    goal: str = "방문과 문의를 늘리기"
    channel: str | None = None
    objective: str | None = None
    schedule: str | None = None
