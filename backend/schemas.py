from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ------------------ Auth Schemas ------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str
    email: str
    full_name: str
    child_id: Optional[int] = None
    parent_id: Optional[int] = None


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: str = "PARENT"
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ------------------ Spending Rule Schemas ------------------
class SpendingRuleBase(BaseModel):
    daily_limit: float = Field(..., ge=0)
    weekly_limit: float = Field(..., ge=0)
    approval_threshold: float = Field(..., ge=0)
    allowed_categories: Optional[str] = "Education,Books,Food & Snacks,Entertainment,Gaming,Shopping,Transport"
    blocked_merchants: Optional[str] = ""
    is_active: bool = True


class SpendingRuleUpdate(SpendingRuleBase):
    pass


class SpendingRuleResponse(SpendingRuleBase):
    id: int
    child_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ------------------ Child Profile Schemas ------------------
class ChildProfileCreate(BaseModel):
    full_name: str
    age: int = Field(..., ge=5, le=18)
    initial_balance: float = 2000.0
    daily_limit: float = 500.0
    weekly_limit: float = 2000.0
    approval_threshold: float = 300.0
    avatar: Optional[str] = "Arjun"


class ChildProfileResponse(BaseModel):
    id: int
    user_id: int
    parent_id: int
    full_name: str
    age: int
    avatar: str
    is_active: bool
    created_at: datetime
    wallet_balance: Optional[float] = 0.0
    total_spent: Optional[float] = 0.0
    spending_rule: Optional[SpendingRuleResponse] = None

    class Config:
        from_attributes = True


# ------------------ Parent Profile Schemas ------------------
class ParentProfileResponse(BaseModel):
    id: int
    user_id: int
    phone: Optional[str] = None
    currency: str
    created_at: datetime
    children: List[ChildProfileResponse] = []

    class Config:
        from_attributes = True


# ------------------ Wallet Schemas ------------------
class WalletResponse(BaseModel):
    id: int
    child_id: int
    currency: str = "USD"
    balance: float
    balance_inr: float = 0.0
    fx_rate: float = 85.0
    total_spent: float
    total_deposited: float
    daily_limit: float
    daily_spent_today: float
    daily_remaining: float
    weekly_limit: float
    weekly_spent: float
    weekly_remaining: float
    approval_threshold: float

    class Config:
        from_attributes = True


class WalletDeposit(BaseModel):
    amount: float = Field(..., gt=0)


class SendMoneyRequest(BaseModel):
    child_id: Optional[int] = None
    amount_inr: float = Field(..., gt=0)
    notes: Optional[str] = "Monthly living & study allowance"
    payment_method: Optional[str] = "PAYPAL_SANDBOX_BALANCE"


class SendMoneyResponse(BaseModel):
    status: str
    message: str
    amount_inr: float
    amount_usd: float
    fx_rate: float
    child_name: str
    new_wallet_balance_usd: float
    new_wallet_balance_inr: float
    transaction_code: str


# ------------------ Transaction & AI Schemas ------------------
class TransactionCreate(BaseModel):
    merchant: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    category: str = "General"
    description: Optional[str] = ""
    payment_method: str = "SIMULATED_WALLET"  # or PAYPAL_SANDBOX
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None


class AIReportResponse(BaseModel):
    id: Optional[int] = None
    transaction_id: Optional[int] = None
    risk_level: str
    category: str
    requires_review: bool
    explanation: str
    spending_summary: str
    recommendation: str
    confidence_score: float = 0.95
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    transaction_code: str
    child_id: int
    child_name: Optional[str] = None
    amount: float
    currency: str
    amount_inr: Optional[float] = None
    amount_usd: Optional[float] = None
    fx_rate: float = 85.0
    merchant: str
    category: str
    description: Optional[str]
    status: str
    payment_method: str
    paypal_order_id: Optional[str]
    paypal_capture_id: Optional[str]
    requires_approval: bool
    remaining_daily_allowance_after: float
    created_at: datetime
    ai_report: Optional[AIReportResponse] = None
    approval_status: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionReceiptResponse(BaseModel):
    report_title: str = "PayPal Sandbox Transaction Receipt & AI Monitoring Report"
    notice: str = "Official parental monitoring and safety verification record. Not a payment invoice."
    child_name: str
    transaction_id: str
    merchant: str
    transaction_amount: float
    currency: str
    amount_inr: Optional[float] = None
    fx_rate: float = 85.0
    transaction_date: str
    payment_status: str
    payment_method: str
    category: str
    risk_assessment: str
    daily_spending_before: float
    daily_spending_after: float
    remaining_spending_allowance: float
    daily_limit: float
    ai_explanation: str
    ai_spending_summary: str
    ai_recommendation: str
    requires_review: bool


# ------------------ Approval Schemas ------------------
class ApprovalActionRequest(BaseModel):
    action: str  # "APPROVE" or "DECLINE"
    notes: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    id: int
    transaction_id: int
    transaction_code: str
    child_id: int
    child_name: str
    merchant: str
    amount: float
    currency: str
    category: str
    status: str
    parent_notes: Optional[str]
    requested_at: datetime
    decided_at: Optional[datetime]
    ai_report: Optional[AIReportResponse] = None

    class Config:
        from_attributes = True


# ------------------ Notification Schemas ------------------
class NotificationResponse(BaseModel):
    id: int
    parent_id: int
    child_id: int
    child_name: Optional[str] = None
    type: str
    title: str
    message: str
    risk_level: str
    transaction_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ------------------ Savings Goals Schemas ------------------
class SavingsGoalCreate(BaseModel):
    title: str
    target_amount: float = Field(..., gt=0)
    current_amount: float = 0.0
    icon: Optional[str] = "Target"
    target_date: Optional[datetime] = None


class SavingsGoalUpdate(BaseModel):
    current_amount: Optional[float] = None
    add_amount: Optional[float] = None
    is_completed: Optional[bool] = None


class SavingsGoalResponse(BaseModel):
    id: int
    child_id: int
    title: str
    target_amount: float
    current_amount: float
    icon: str
    target_date: Optional[datetime]
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ------------------ AI Parent Assistant Schemas ------------------
class AIAssistantQueryRequest(BaseModel):
    prompt: str
    child_id: Optional[int] = None


class AIAssistantQueryResponse(BaseModel):
    reply: str
    context_data: Optional[Dict[str, Any]] = None
    suggested_questions: List[str] = []


# ------------------ PayPal Sandbox Schemas ------------------
class PayPalOrderCreateRequest(BaseModel):
    child_id: int
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    merchant: str
    category: str
    description: Optional[str] = ""


class PayPalCaptureRequest(BaseModel):
    order_id: str
    child_id: int
    merchant: str
    category: str
    description: Optional[str] = ""
    amount: float
    currency: str = "USD"
