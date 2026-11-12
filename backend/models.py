import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from backend.database import Base


class UserRole(str, enum.Enum):
    PARENT = "PARENT"
    CHILD = "CHILD"
    ADMIN = "ADMIN"


class TransactionStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    DECLINED = "DECLINED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    PAYPAL_SANDBOX = "PAYPAL_SANDBOX"
    SIMULATED_WALLET = "SIMULATED_WALLET"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class NotificationType(str, enum.Enum):
    PURCHASE = "PURCHASE"
    THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED"
    DAILY_LIMIT_REACHED = "DAILY_LIMIT_REACHED"
    WEEKLY_LIMIT_REACHED = "WEEKLY_LIMIT_REACHED"
    UNUSUAL_PATTERN = "UNUSUAL_PATTERN"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND = "REFUND"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.PARENT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent_profile = relationship("ParentProfile", back_populates="user", uselist=False)
    child_profile = relationship("ChildProfile", back_populates="user", uselist=False)


class ParentProfile(Base):
    __tablename__ = "parent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    phone = Column(String(50), nullable=True)
    currency = Column(String(10), default="INR")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="parent_profile")
    children = relationship("ChildProfile", back_populates="parent", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="parent", cascade="all, delete-orphan")
    approvals = relationship("ApprovalRequest", back_populates="parent", cascade="all, delete-orphan")


class ChildProfile(Base):
    __tablename__ = "child_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("parent_profiles.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    age = Column(Integer, default=12)
    avatar = Column(String(255), default="default_avatar.png")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="child_profile")
    parent = relationship("ParentProfile", back_populates="children")
    wallet = relationship("WalletAccount", back_populates="child", uselist=False, cascade="all, delete-orphan")
    spending_rule = relationship("SpendingRule", back_populates="child", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="child", cascade="all, delete-orphan")
    savings_goals = relationship("SavingsGoal", back_populates="child", cascade="all, delete-orphan")


class WalletAccount(Base):
    __tablename__ = "wallet_accounts"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    currency = Column(String(10), default="INR")
    balance = Column(Float, default=2000.0)
    total_spent = Column(Float, default=0.0)
    total_deposited = Column(Float, default=2000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    child = relationship("ChildProfile", back_populates="wallet")


class SpendingRule(Base):
    __tablename__ = "spending_rules"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    daily_limit = Column(Float, default=500.0)
    weekly_limit = Column(Float, default=2000.0)
    approval_threshold = Column(Float, default=300.0)
    allowed_categories = Column(Text, default="Education,Books,Food & Snacks,Entertainment,Gaming,Shopping,Transport")
    blocked_merchants = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    child = relationship("ChildProfile", back_populates="spending_rule")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_code = Column(String(50), unique=True, index=True, nullable=False)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    merchant = Column(String(255), nullable=False)
    category = Column(String(100), default="General")
    description = Column(String(500), default="")
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.COMPLETED, nullable=False)
    payment_method = Column(SAEnum(PaymentMethod), default=PaymentMethod.SIMULATED_WALLET, nullable=False)
    paypal_order_id = Column(String(100), nullable=True)
    paypal_capture_id = Column(String(100), nullable=True)
    requires_approval = Column(Boolean, default=False)
    remaining_daily_allowance_after = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    child = relationship("ChildProfile", back_populates="transactions")
    ai_report = relationship("AIReport", back_populates="transaction", uselist=False, cascade="all, delete-orphan")
    approval_request = relationship("ApprovalRequest", back_populates="transaction", uselist=False, cascade="all, delete-orphan")


class AIReport(Base):
    __tablename__ = "ai_reports"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.LOW, nullable=False)
    category = Column(String(100), default="General")
    requires_review = Column(Boolean, default=False)
    explanation = Column(Text, nullable=False)
    spending_summary = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.95)
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="ai_report")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("parent_profiles.id", ondelete="CASCADE"), nullable=False)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    parent_notes = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

    transaction = relationship("Transaction", back_populates="approval_request")
    parent = relationship("ParentProfile", back_populates="approvals")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parent_profiles.id", ondelete="CASCADE"), nullable=False)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False)
    type = Column(SAEnum(NotificationType), default=NotificationType.PURCHASE, nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.LOW, nullable=False)
    transaction_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("ParentProfile", back_populates="notifications")


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    icon = Column(String(50), default="Target")
    target_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    child = relationship("ChildProfile", back_populates="savings_goals")


class PayPalOrder(Base):
    __tablename__ = "paypal_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    child_id = Column(Integer, ForeignKey("child_profiles.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="CREATED")
    intent = Column(String(50), default="CAPTURE")
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PayPalCapture(Base):
    __tablename__ = "paypal_captures"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(String(100), unique=True, index=True, nullable=False)
    order_id = Column(String(100), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="COMPLETED")
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebhookEventRecord(Base):
    __tablename__ = "webhook_event_records"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
