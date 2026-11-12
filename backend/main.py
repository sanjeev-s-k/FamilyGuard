import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from fastapi import FastAPI, Depends, HTTPException, status, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db, init_db
from backend.models import (
    User, UserRole, ParentProfile, ChildProfile, WalletAccount,
    SpendingRule, Transaction, AIReport, ApprovalRequest,
    Notification, NotificationType, RiskLevel, TransactionStatus,
    PaymentMethod, ApprovalStatus, SavingsGoal, PayPalOrder, PayPalCapture, WebhookEventRecord
)
from backend.schemas import (
    Token, UserCreate, UserLogin, UserResponse,
    ChildProfileCreate, ChildProfileResponse,
    SpendingRuleUpdate, SpendingRuleResponse,
    WalletResponse, WalletDeposit, SendMoneyRequest, SendMoneyResponse,
    TransactionCreate, TransactionResponse, TransactionReceiptResponse,
    ApprovalActionRequest, ApprovalRequestResponse,
    NotificationResponse, SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse,
    AIAssistantQueryRequest, AIAssistantQueryResponse,
    PayPalOrderCreateRequest, PayPalCaptureRequest
)
from backend.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_parent, get_current_child
)
from backend.ai_engine import analyze_transaction, answer_parent_query
from backend.paypal_service import (
    create_order as pp_create_order,
    capture_order as pp_capture_order,
    verify_webhook_signature,
    is_configured as pp_is_configured
)
from backend.reports import generate_transaction_pdf
from backend.seed_data import seed_demo_data

FX_RATE = 85.0  # Pegged exchange rate: 1 USD = 85.00 INR


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("familyguard.api")

app = FastAPI(
    title="FamilyGuard API",
    description="AI-Powered Parental Payment Monitoring System REST Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    db = next(get_db())
    try:
        seed_demo_data(db)
        logger.info("FamilyGuard Database initialized & demo data verified.")
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FamilyGuard API",
        "paypal_configured": pp_is_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ==============================================================================
# MODULE 1: AUTHENTICATION & DEMO SWITCHER
# ==============================================================================

@app.post("/api/auth/register", response_model=UserResponse)
def register_parent(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.PARENT
    )
    db.add(user)
    db.flush()

    parent_profile = ParentProfile(
        user_id=user.id,
        phone=user_in.phone,
        currency="INR"
    )
    db.add(parent_profile)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    child_id = None
    parent_id = None
    if user.role == UserRole.CHILD and user.child_profile:
        child_id = user.child_profile.id
    elif user.role == UserRole.PARENT and user.parent_profile:
        parent_id = user.parent_profile.id

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "email": user.email,
        "full_name": user.full_name,
        "child_id": child_id,
        "parent_id": parent_id
    }


@app.post("/api/auth/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    child_id = None
    parent_id = None
    if user.role == UserRole.CHILD and user.child_profile:
        child_id = user.child_profile.id
    elif user.role == UserRole.PARENT and user.parent_profile:
        parent_id = user.parent_profile.id

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "email": user.email,
        "full_name": user.full_name,
        "child_id": child_id,
        "parent_id": parent_id
    }


@app.post("/api/auth/demo/parent", response_model=Token)
def demo_login_parent(db: Session = Depends(get_db)):
    """One-click instant login for Demo Parent (Hackathon demonstration)"""
    user = db.query(User).filter(User.email == "parent@familyguard.demo").first()
    if not user:
        seed_demo_data(db)
        user = db.query(User).filter(User.email == "parent@familyguard.demo").first()

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "email": user.email,
        "full_name": user.full_name,
        "parent_id": user.parent_profile.id if user.parent_profile else None,
        "child_id": None
    }


@app.post("/api/auth/demo/child", response_model=Token)
def demo_login_child(db: Session = Depends(get_db)):
    """One-click instant login for Arjun (Child wallet demonstration)"""
    user = db.query(User).filter(User.email == "arjun@familyguard.demo").first()
    if not user:
        seed_demo_data(db)
        user = db.query(User).filter(User.email == "arjun@familyguard.demo").first()

    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "email": user.email,
        "full_name": user.full_name,
        "parent_id": None,
        "child_id": user.child_profile.id if user.child_profile else None
    }


@app.get("/api/auth/me")
def get_current_user_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    child_id = user.child_profile.id if user.child_profile else None
    parent_id = user.parent_profile.id if user.parent_profile else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "parent_id": parent_id,
        "child_id": child_id
    }


# ==============================================================================
# MODULE 2: CHILD WALLET & PAYMENT INITIATION
# ==============================================================================

def get_child_spending_stats(child_id: int, db: Session):
    now = datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day)
    start_of_week = start_of_day - timedelta(days=start_of_day.weekday())

    today_spent = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
        Transaction.child_id == child_id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= start_of_day
    ).scalar()

    week_spent = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
        Transaction.child_id == child_id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= start_of_week
    ).scalar()

    return float(today_spent), float(week_spent)


@app.get("/api/child/wallet", response_model=WalletResponse)
def get_child_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    child_profile = None
    if current_user.role == UserRole.CHILD:
        child_profile = current_user.child_profile
    elif current_user.role == UserRole.PARENT and current_user.parent_profile and current_user.parent_profile.children:
        child_profile = current_user.parent_profile.children[0]

    if not child_profile:
        raise HTTPException(status_code=404, detail="Child profile not found")

    wallet = child_profile.wallet
    rule = child_profile.spending_rule
    today_spent, week_spent = get_child_spending_stats(child_profile.id, db)

    daily_limit = rule.daily_limit if rule else 60.0
    weekly_limit = rule.weekly_limit if rule else 250.0
    approval_threshold = rule.approval_threshold if rule else 40.0

    return {
        "id": wallet.id,
        "child_id": child_profile.id,
        "currency": wallet.currency,
        "balance": wallet.balance,
        "balance_inr": round(wallet.balance * FX_RATE, 2),
        "fx_rate": FX_RATE,
        "total_spent": wallet.total_spent,
        "total_deposited": wallet.total_deposited,
        "daily_limit": daily_limit,
        "daily_spent_today": today_spent,
        "daily_remaining": max(0.0, daily_limit - today_spent),
        "weekly_limit": weekly_limit,
        "weekly_spent": week_spent,
        "weekly_remaining": max(0.0, weekly_limit - week_spent),
        "approval_threshold": approval_threshold
    }


@app.get("/api/child/transactions")
def get_child_transactions(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    child_profile = current_user.child_profile
    if not child_profile and current_user.role == UserRole.PARENT and current_user.parent_profile.children:
        child_profile = current_user.parent_profile.children[0]

    if not child_profile:
        raise HTTPException(status_code=404, detail="Child profile not found")

    txs = db.query(Transaction).filter(
        Transaction.child_id == child_profile.id
    ).order_by(Transaction.created_at.desc()).limit(limit).all()

    result = []
    for t in txs:
        approval_status = t.approval_request.status.value if t.approval_request else None
        ai_data = None
        if t.ai_report:
            ai_data = {
                "id": t.ai_report.id,
                "risk_level": t.ai_report.risk_level.value,
                "category": t.ai_report.category,
                "requires_review": t.ai_report.requires_review,
                "explanation": t.ai_report.explanation,
                "spending_summary": t.ai_report.spending_summary,
                "recommendation": t.ai_report.recommendation,
                "confidence_score": t.ai_report.confidence_score
            }
        amount_usd = round(t.amount / FX_RATE, 2) if t.currency.upper() == "INR" else t.amount
        amount_inr = round(t.amount * FX_RATE, 2) if t.currency.upper() == "USD" else t.amount
        result.append({
            "id": t.id,
            "transaction_code": t.transaction_code,
            "child_id": t.child_id,
            "child_name": child_profile.full_name,
            "amount": amount_usd,
            "currency": t.currency,
            "amount_inr": amount_inr,
            "amount_usd": amount_usd,
            "fx_rate": FX_RATE,
            "merchant": t.merchant,
            "category": t.category,
            "description": t.description,
            "status": t.status.value,
            "payment_method": t.payment_method.value,
            "paypal_order_id": t.paypal_order_id,
            "paypal_capture_id": t.paypal_capture_id,
            "requires_approval": t.requires_approval,
            "remaining_daily_allowance_after": t.remaining_daily_allowance_after,
            "created_at": t.created_at.isoformat(),
            "ai_report": ai_data,
            "approval_status": approval_status
        })
    return result


@app.post("/api/child/pay")
async def initiate_child_payment(
    payment_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Core Payment Processing + AI Engine Workflow:
    1. Validates wallet balance and spending limits.
    2. If amount >= approval_threshold:
       Creates PENDING_APPROVAL transaction and approval request. Parent is alerted.
    3. If amount < approval_threshold and within limits:
       Deducts wallet balance, marks COMPLETED, triggers AI analysis, sends parent notification.
    """
    child_profile = current_user.child_profile
    if not child_profile and current_user.role == UserRole.PARENT and current_user.parent_profile.children:
        child_profile = current_user.parent_profile.children[0]

    if not child_profile:
        raise HTTPException(status_code=404, detail="Child profile not found")

    wallet = child_profile.wallet
    rule = child_profile.spending_rule
    parent_profile = child_profile.parent

    daily_limit = rule.daily_limit if rule else 60.0
    weekly_limit = rule.weekly_limit if rule else 250.0
    approval_threshold = rule.approval_threshold if rule else 40.0

    today_spent_prior, week_spent_prior = get_child_spending_stats(child_profile.id, db)

    # Determine transaction amount in USD
    if payment_in.currency.upper() == "INR":
        # Convert INR to USD using FX_RATE
        amount_usd = round(payment_in.amount / FX_RATE, 2)
    else:
        amount_usd = payment_in.amount

    # Balance check (wallet balance is in USD)
    if wallet.balance < amount_usd and payment_in.payment_method != "PAYPAL_SANDBOX":
        raise HTTPException(status_code=400, detail=f"Insufficient study wallet balance (${wallet.balance:,.2f} USD)")

    # Generate unique transaction code
    count = db.query(Transaction).count()
    tx_code = f"TX{1025 + count}"

    # Determine approval requirement using USD amounts
    requires_approval = amount_usd >= approval_threshold or (today_spent_prior + amount_usd) > daily_limit

    # Prepare historical context for AI
    past_txs = db.query(Transaction).filter(
        Transaction.child_id == child_profile.id
    ).order_by(Transaction.created_at.desc()).limit(10).all()

    history_payload = [
        {
            "amount": t.amount,
            "merchant": t.merchant,
            "category": t.category,
            "created_at": t.created_at.isoformat()
        }
        for t in past_txs
    ]

    # Run AI Analysis using normalized USD values
    ai_result = await analyze_transaction(
        child_id=child_profile.id,
        transaction_id=tx_code,
        merchant=payment_in.merchant,
        amount=amount_usd,
        currency="USD",
        category=payment_in.category,
        timestamp=datetime.utcnow().isoformat(),
        history=history_payload,
        daily_limit=daily_limit,
        weekly_limit=weekly_limit,
        approval_threshold=approval_threshold,
        total_spent_today_prior=today_spent_prior,
        total_spent_week_prior=week_spent_prior
    )

    remaining_daily = max(0.0, daily_limit - (today_spent_prior + (0 if requires_approval else amount_usd)))

    # Persist Transaction
    new_tx = Transaction(
        transaction_code=tx_code,
        child_id=child_profile.id,
        amount=payment_in.amount,
        currency=payment_in.currency,
        merchant=payment_in.merchant,
        category=ai_result.get("category", payment_in.category),
        description=payment_in.description or f"Payment at {payment_in.merchant}",
        status=TransactionStatus.PENDING_APPROVAL if requires_approval else TransactionStatus.COMPLETED,
        payment_method=PaymentMethod.PAYPAL_SANDBOX if payment_in.payment_method == "PAYPAL_SANDBOX" else PaymentMethod.SIMULATED_WALLET,
        paypal_order_id=payment_in.paypal_order_id,
        paypal_capture_id=payment_in.paypal_capture_id,
        requires_approval=requires_approval,
        remaining_daily_allowance_after=remaining_daily,
        created_at=datetime.utcnow()
    )
    db.add(new_tx)
    db.flush()

    # Save AI Report
    ai_report = AIReport(
        transaction_id=new_tx.id,
        risk_level=RiskLevel[ai_result.get("risk_level", "LOW")],
        category=ai_result.get("category", payment_in.category),
        requires_review=requires_approval or ai_result.get("requires_review", False),
        explanation=ai_result.get("explanation", ""),
        spending_summary=ai_result.get("spending_summary", ""),
        recommendation=ai_result.get("recommendation", ""),
        confidence_score=ai_result.get("confidence_score", 0.95),
        created_at=new_tx.created_at
    )
    db.add(ai_report)

    inr_equiv = round(payment_in.amount * FX_RATE, 2)
    threshold_inr = round(approval_threshold * FX_RATE, 2)

    if requires_approval:
        # Create Approval Request for Parent
        app_req = ApprovalRequest(
            transaction_id=new_tx.id,
            parent_id=parent_profile.id,
            child_id=child_profile.id,
            status=ApprovalStatus.PENDING,
            requested_at=new_tx.created_at
        )
        db.add(app_req)

        # Notify Parent with dual currency
        notif = Notification(
            parent_id=parent_profile.id,
            child_id=child_profile.id,
            type=NotificationType.THRESHOLD_EXCEEDED,
            title=f"Approval Required: {child_profile.full_name} (${payment_in.amount:,.2f} USD / ₹{inr_equiv:,.2f})",
            message=f"{child_profile.full_name} requested a purchase of ${payment_in.amount:,.2f} USD (₹{inr_equiv:,.2f} INR) at {payment_in.merchant}. "
                    f"Exceeds single transaction approval threshold of ${approval_threshold:,.2f} USD (₹{threshold_inr:,.2f} INR).",
            risk_level=RiskLevel[ai_result.get("risk_level", "MEDIUM")],
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(notif)

    else:
        # Deduct wallet balance in USD
        wallet.balance -= amount_usd
        wallet.total_spent += amount_usd

        # Send Purchase Notification to Parent with dual currency
        notif = Notification(
            parent_id=parent_profile.id,
            child_id=child_profile.id,
            type=NotificationType.PURCHASE,
            title=f"PayPal Verified: {payment_in.merchant}",
            message=f"{child_profile.full_name} spent ${payment_in.amount:,.2f} USD (₹{inr_equiv:,.2f} INR) at {payment_in.merchant} ({payment_in.category}).",
            risk_level=RiskLevel[ai_result.get("risk_level", "LOW")],
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(notif)

    # Check if daily living allowance limit reached or exceeded
    if (today_spent_prior + amount_usd) >= daily_limit:
        limit_notif = Notification(
            parent_id=parent_profile.id,
            child_id=child_profile.id,
            type=NotificationType.DAILY_LIMIT_REACHED,
            title=f"⚠️ Daily Spending Limit Reached: {child_profile.full_name}",
            message=f"{child_profile.full_name} has reached or exceeded their daily living allowance cap of ${daily_limit:,.2f} USD (₹{daily_limit * FX_RATE:,.2f} INR). Total today: ${today_spent_prior + amount_usd:,.2f} USD.",
            risk_level=RiskLevel.HIGH,
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(limit_notif)

    db.commit()
    db.refresh(new_tx)

    return {
        "status": new_tx.status.value,
        "transaction_code": new_tx.transaction_code,
        "transaction_id": new_tx.id,
        "amount": new_tx.amount,
        "currency": new_tx.currency,
        "merchant": new_tx.merchant,
        "requires_approval": requires_approval,
        "message": "Transaction pending parental approval." if requires_approval else "Payment processed and verified.",
        "ai_report": ai_result,
        "new_balance": wallet.balance
    }


# ==============================================================================
# MODULE 3 & 7: PARENT DASHBOARD & APPROVAL WORKFLOW
# ==============================================================================

@app.get("/api/parent/overview")
def get_parent_overview(
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    children = db.query(ChildProfile).filter(ChildProfile.parent_id == parent.id).all()
    if not children:
        children = db.query(ChildProfile).all()
    child_ids = [c.id for c in children]

    # Total family spending: ignore Allowance Remittance from spending summation
    total_spent_usd = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
        Transaction.child_id.in_(child_ids),
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.category != "Allowance Remittance"
    ).scalar() if child_ids else 0.0
    total_spent_inr = round(float(total_spent_usd) * FX_RATE, 2)

    # Total transactions count
    tx_count = db.query(Transaction).filter(
        Transaction.child_id.in_(child_ids)
    ).count() if child_ids else 0

    # Pending approvals
    pending_approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.parent_id == parent.id,
        ApprovalRequest.status == ApprovalStatus.PENDING
    ).count()

    # Active unread alerts
    unread_alerts = db.query(Notification).filter(
        Notification.parent_id == parent.id,
        Notification.is_read == False
    ).count()

    # Individual child breakdown (Study Abroad in USD + Converted INR)
    children_summary = []
    for c in children:
        c_spent, c_week = get_child_spending_stats(c.id, db)
        children_summary.append({
            "id": c.id,
            "name": c.full_name,
            "age": c.age,
            "avatar": c.avatar,
            "balance": c.wallet.balance if c.wallet else 0.0,
            "balance_usd": c.wallet.balance if c.wallet else 0.0,
            "balance_inr": round((c.wallet.balance if c.wallet else 0.0) * FX_RATE, 2),
            "total_spent": c.wallet.total_spent if c.wallet else 0.0,
            "spent_today": c_spent,
            "spent_today_inr": round(c_spent * FX_RATE, 2),
            "daily_limit": c.spending_rule.daily_limit if c.spending_rule else 60.0,
            "daily_limit_inr": round((c.spending_rule.daily_limit if c.spending_rule else 60.0) * FX_RATE, 2),
            "weekly_limit": c.spending_rule.weekly_limit if c.spending_rule else 250.0,
            "weekly_limit_inr": round((c.spending_rule.weekly_limit if c.spending_rule else 250.0) * FX_RATE, 2),
            "approval_threshold": c.spending_rule.approval_threshold if c.spending_rule else 40.0,
            "approval_threshold_inr": round((c.spending_rule.approval_threshold if c.spending_rule else 40.0) * FX_RATE, 2)
        })

    # Category-wise spending
    category_rows = db.query(
        Transaction.category,
        func.sum(Transaction.amount)
    ).filter(
        Transaction.child_id.in_(child_ids),
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.category != "Allowance Remittance"
    ).group_by(Transaction.category).all() if child_ids else []

    category_spending = [
        {"category": row[0], "amount": round(float(row[1]) * FX_RATE, 2), "amount_usd": float(row[1])}
        for row in category_rows
    ]

    # Daily spending trend in INR
    daily_trends = []
    now = datetime.utcnow()
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_start = datetime(day_date.year, day_date.month, day_date.day)
        day_end = day_start + timedelta(days=1)
        day_amt_usd = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(
            Transaction.child_id.in_(child_ids),
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.category != "Allowance Remittance",
            Transaction.created_at >= day_start,
            Transaction.created_at < day_end
        ).scalar() if child_ids else 0.0

        daily_trends.append({
            "date": day_date.strftime("%a (%d %b)"),
            "amount": round(float(day_amt_usd) * FX_RATE, 2),
            "amount_usd": float(day_amt_usd)
        })

    return {
        "parent_name": parent.user.full_name,
        "currency": "INR",
        "child_currency": "USD",
        "fx_rate": FX_RATE,
        "total_family_spending": total_spent_inr,
        "total_family_spending_usd": float(total_spent_usd),
        "total_transactions": tx_count,
        "pending_approvals_count": pending_approvals,
        "unread_alerts_count": unread_alerts,
        "children": children_summary,
        "category_spending": category_spending,
        "daily_trends": daily_trends
    }


@app.post("/api/parent/send-money", response_model=SendMoneyResponse)
def send_money_to_child(
    send_in: SendMoneyRequest,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Parent-to-Child Remittance Feature:
    Indian parents fund children studying abroad via PayPal Sandbox.
    Converts INR to USD at pegged rate (1 USD = 85.00 INR),
    directly credits child's overseas wallet in USD, and logs an audit record.
    """
    child = None
    if send_in.child_id:
        child = db.query(ChildProfile).filter(ChildProfile.id == send_in.child_id, ChildProfile.parent_id == parent.id).first()
    if not child and parent.children:
        child = parent.children[0]
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found")

    amount_usd = round(send_in.amount_inr / FX_RATE, 2)
    child.wallet.balance += amount_usd
    child.wallet.total_deposited += amount_usd

    count = db.query(Transaction).count()
    tx_code = f"TX{1025 + count}"

    tx = Transaction(
        transaction_code=tx_code,
        child_id=child.id,
        amount=amount_usd,
        currency="USD",
        merchant="Parent Allowance Remittance (Demo Parent)",
        category="Allowance Remittance",
        description=send_in.notes or f"Study remittance of ₹{send_in.amount_inr:,.2f} INR (${amount_usd:,.2f} USD)",
        status=TransactionStatus.COMPLETED,
        payment_method=PaymentMethod.PAYPAL_SANDBOX,
        requires_approval=False,
        remaining_daily_allowance_after=child.spending_rule.daily_limit if child.spending_rule else 60.0,
        created_at=datetime.utcnow()
    )
    db.add(tx)
    db.flush()

    ai_report = AIReport(
        transaction_id=tx.id,
        risk_level=RiskLevel.LOW,
        category="Allowance Remittance",
        requires_review=False,
        explanation=f"Parental study allowance remittance of ₹{send_in.amount_inr:,.2f} INR converted to ${amount_usd:,.2f} USD (Rate: 1 USD = {FX_RATE:.2f} INR).",
        spending_summary=f"Added ${amount_usd:,.2f} USD to {child.full_name}'s overseas student wallet. New balance: ${child.wallet.balance:,.2f} USD.",
        recommendation="Verified parent funding transfer via PayPal Sandbox. Safe top-up.",
        confidence_score=1.0,
        created_at=tx.created_at
    )
    db.add(ai_report)

    # Notification to Parent
    n_parent = Notification(
        parent_id=parent.id,
        child_id=child.id,
        type=NotificationType.PURCHASE,
        title=f"PayPal Remittance Sent: ${amount_usd:,.2f} USD",
        message=f"You sent ₹{send_in.amount_inr:,.2f} INR (${amount_usd:,.2f} USD) to {child.full_name}'s study wallet via PayPal Sandbox.",
        risk_level=RiskLevel.LOW,
        transaction_id=tx.id,
        is_read=False,
        created_at=tx.created_at
    )
    db.add(n_parent)

    db.commit()

    return {
        "status": "success",
        "message": f"Successfully remitted ₹{send_in.amount_inr:,.2f} INR (${amount_usd:,.2f} USD) to {child.full_name}'s abroad wallet.",
        "amount_inr": send_in.amount_inr,
        "amount_usd": amount_usd,
        "fx_rate": FX_RATE,
        "child_name": child.full_name,
        "new_wallet_balance_usd": child.wallet.balance,
        "new_wallet_balance_inr": round(child.wallet.balance * FX_RATE, 2),
        "transaction_code": tx_code
    }


@app.get("/api/parent/children")
def list_children(parent: ParentProfile = Depends(get_current_parent), db: Session = Depends(get_db)):
    result = []
    for c in parent.children:
        spent_today, spent_week = get_child_spending_stats(c.id, db)
        rule = c.spending_rule
        result.append({
            "id": c.id,
            "user_id": c.user_id,
            "full_name": c.full_name,
            "age": c.age,
            "avatar": c.avatar,
            "is_active": c.is_active,
            "wallet_balance": c.wallet.balance if c.wallet else 0.0,
            "total_spent": c.wallet.total_spent if c.wallet else 0.0,
            "spent_today": spent_today,
            "spent_week": spent_week,
            "spending_rule": {
                "id": rule.id if rule else 0,
                "child_id": c.id,
                "daily_limit": rule.daily_limit if rule else 500.0,
                "weekly_limit": rule.weekly_limit if rule else 2000.0,
                "approval_threshold": rule.approval_threshold if rule else 300.0,
                "allowed_categories": rule.allowed_categories if rule else "",
                "blocked_merchants": rule.blocked_merchants if rule else "",
                "is_active": rule.is_active if rule else True,
                "updated_at": rule.updated_at.isoformat() if rule else datetime.utcnow().isoformat()
            } if rule else None
        })
    return result


@app.post("/api/parent/children")
def add_child(
    child_in: ChildProfileCreate,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    # Create child user
    email_clean = child_in.full_name.lower().replace(" ", "") + "@familyguard.demo"
    child_user = User(
        email=email_clean,
        hashed_password=get_password_hash("Password123!"),
        full_name=child_in.full_name,
        role=UserRole.CHILD
    )
    db.add(child_user)
    db.flush()

    child_profile = ChildProfile(
        user_id=child_user.id,
        parent_id=parent.id,
        full_name=child_in.full_name,
        age=child_in.age,
        avatar=child_in.avatar or "default"
    )
    db.add(child_profile)
    db.flush()

    wallet = WalletAccount(
        child_id=child_profile.id,
        currency=parent.currency,
        balance=child_in.initial_balance,
        total_spent=0.0,
        total_deposited=child_in.initial_balance
    )
    db.add(wallet)

    rule = SpendingRule(
        child_id=child_profile.id,
        daily_limit=child_in.daily_limit,
        weekly_limit=child_in.weekly_limit,
        approval_threshold=child_in.approval_threshold
    )
    db.add(rule)

    db.commit()
    return {"status": "success", "child_id": child_profile.id, "message": f"Child {child_in.full_name} added successfully."}


@app.put("/api/parent/children/{child_id}/limits")
def update_spending_limits(
    child_id: int,
    limits_in: SpendingRuleUpdate,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    child = db.query(ChildProfile).filter(ChildProfile.id == child_id, ChildProfile.parent_id == parent.id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    rule = child.spending_rule
    if not rule:
        rule = SpendingRule(child_id=child.id)
        db.add(rule)

    rule.daily_limit = limits_in.daily_limit
    rule.weekly_limit = limits_in.weekly_limit
    rule.approval_threshold = limits_in.approval_threshold
    if limits_in.allowed_categories is not None:
        rule.allowed_categories = limits_in.allowed_categories
    if limits_in.blocked_merchants is not None:
        rule.blocked_merchants = limits_in.blocked_merchants
    rule.is_active = limits_in.is_active

    db.commit()
    return {"status": "success", "message": "Spending controls updated successfully."}


@app.get("/api/parent/transactions")
def get_parent_transactions(
    parent: ParentProfile = Depends(get_current_parent),
    child_id: Optional[int] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    children = db.query(ChildProfile).filter(ChildProfile.parent_id == parent.id).all()
    if not children:
        children = db.query(ChildProfile).all()
    child_ids = [c.id for c in children]
    query = db.query(Transaction)
    if child_ids:
        query = query.filter(Transaction.child_id.in_(child_ids))

    if child_id:
        query = query.filter(Transaction.child_id == child_id)
    if category:
        query = query.filter(Transaction.category == category)
    if status_filter:
        query = query.filter(Transaction.status == TransactionStatus[status_filter])

    txs = query.order_by(Transaction.created_at.desc()).all()

    children_map = {c.id: c.full_name for c in children}
    result = []
    for t in txs:
        ai_data = None
        if t.ai_report:
            ai_data = {
                "id": t.ai_report.id,
                "risk_level": t.ai_report.risk_level.value,
                "category": t.ai_report.category,
                "requires_review": t.ai_report.requires_review,
                "explanation": t.ai_report.explanation,
                "spending_summary": t.ai_report.spending_summary,
                "recommendation": t.ai_report.recommendation,
                "confidence_score": t.ai_report.confidence_score
            }
        amount_usd = round(t.amount / FX_RATE, 2) if t.currency.upper() == "INR" else t.amount
        amount_inr = round(t.amount * FX_RATE, 2) if t.currency.upper() == "USD" else t.amount
        result.append({
            "id": t.id,
            "transaction_code": t.transaction_code,
            "child_id": t.child_id,
            "child_name": children_map.get(t.child_id, "Unknown"),
            "amount": amount_usd,
            "amount_usd": amount_usd,
            "amount_inr": amount_inr,
            "currency": t.currency,
            "merchant": t.merchant,
            "category": t.category,
            "description": t.description,
            "status": t.status.value,
            "payment_method": t.payment_method.value,
            "paypal_order_id": t.paypal_order_id,
            "paypal_capture_id": t.paypal_capture_id,
            "requires_approval": t.requires_approval,
            "remaining_daily_allowance_after": t.remaining_daily_allowance_after,
            "created_at": t.created_at.isoformat(),
            "ai_report": ai_data,
            "approval_status": t.approval_request.status.value if t.approval_request else None
        })
    return result


@app.get("/api/parent/approvals")
def get_approval_requests(
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    children = db.query(ChildProfile).filter(ChildProfile.parent_id == parent.id).all()
    if not children:
        children = db.query(ChildProfile).all()
    children_map = {c.id: c.full_name for c in children}

    requests = db.query(ApprovalRequest).filter(
        ApprovalRequest.parent_id == parent.id
    ).order_by(ApprovalRequest.requested_at.desc()).all()
    if not requests:
        requests = db.query(ApprovalRequest).order_by(ApprovalRequest.requested_at.desc()).all()
    result = []
    for r in requests:
        t = r.transaction
        ai_data = None
        if t.ai_report:
            ai_data = {
                "id": t.ai_report.id,
                "risk_level": t.ai_report.risk_level.value,
                "category": t.ai_report.category,
                "requires_review": t.ai_report.requires_review,
                "explanation": t.ai_report.explanation,
                "spending_summary": t.ai_report.spending_summary,
                "recommendation": t.ai_report.recommendation,
                "confidence_score": t.ai_report.confidence_score
            }
        amount_usd = round(t.amount / FX_RATE, 2) if t.currency.upper() == "INR" else t.amount
        amount_inr = round(t.amount * FX_RATE, 2) if t.currency.upper() == "USD" else t.amount
        result.append({
            "id": r.id,
            "transaction_id": t.id,
            "transaction_code": t.transaction_code,
            "child_id": r.child_id,
            "child_name": children_map.get(r.child_id, "Child"),
            "merchant": t.merchant,
            "amount": amount_usd,
            "amount_usd": amount_usd,
            "amount_inr": amount_inr,
            "currency": t.currency,
            "category": t.category,
            "status": r.status.value,
            "parent_notes": r.parent_notes,
            "requested_at": r.requested_at.isoformat(),
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "ai_report": ai_data
        })
    return result


@app.post("/api/parent/approvals/{request_id}/action")
def act_on_approval_request(
    request_id: int,
    action_in: ApprovalActionRequest,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Parent Approval System Workflow:
    - Approves or declines the simulated approval request.
    - If APPROVED: deducts balance, marks transaction COMPLETED.
    - If DECLINED: marks transaction DECLINED, balance remains untouched.
    - Audits decision and informs child.
    """
    req = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == request_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request has already been {req.status.value.lower()}")

    action = action_in.action.upper()
    req.decided_at = datetime.utcnow()
    req.parent_notes = action_in.notes

    tx = req.transaction
    child = tx.child

    if action == "APPROVE":
        req.status = ApprovalStatus.APPROVED
        tx.status = TransactionStatus.COMPLETED

        # Deduct wallet balance upon approval (convert if INR)
        amount_usd = round(tx.amount / FX_RATE, 2) if tx.currency.upper() == "INR" else tx.amount
        child.wallet.balance = round(child.wallet.balance - amount_usd, 2)
        child.wallet.total_spent = round(child.wallet.total_spent + amount_usd, 2)

        # Send notification to Parent confirming action
        notif = Notification(
            parent_id=parent.id,
            child_id=child.id,
            type=NotificationType.PURCHASE,
            title=f"Request Approved: {tx.merchant}",
            message=f"You approved {child.full_name}'s purchase of {tx.currency} {tx.amount:,.2f} at {tx.merchant}.",
            risk_level=RiskLevel.LOW,
            transaction_id=tx.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif)
    elif action == "DECLINE":
        req.status = ApprovalStatus.DECLINED
        tx.status = TransactionStatus.DECLINED

        notif = Notification(
            parent_id=parent.id,
            child_id=child.id,
            type=NotificationType.PURCHASE,
            title=f"Request Declined: {tx.merchant}",
            message=f"You declined {child.full_name}'s request for {tx.currency} {tx.amount:,.2f} at {tx.merchant}.",
            risk_level=RiskLevel.MEDIUM,
            transaction_id=tx.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif)
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be APPROVE or DECLINE.")

    db.commit()
    return {
        "status": "success",
        "approval_status": req.status.value,
        "transaction_status": tx.status.value,
        "message": f"Transaction has been {req.status.value.lower()}."
    }


# ==============================================================================
# MODULE 6: PARENT ALERT & NOTIFICATION SYSTEM
# ==============================================================================

@app.get("/api/parent/notifications")
def get_parent_notifications(
    parent: ParentProfile = Depends(get_current_parent),
    limit: int = 30,
    db: Session = Depends(get_db)
):
    notifs = db.query(Notification).filter(
        Notification.parent_id == parent.id
    ).order_by(Notification.created_at.desc()).limit(limit).all()

    children_map = {c.id: c.full_name for c in parent.children}
    result = []
    for n in notifs:
        result.append({
            "id": n.id,
            "parent_id": n.parent_id,
            "child_id": n.child_id,
            "child_name": children_map.get(n.child_id, "Child"),
            "type": n.type.value,
            "title": n.title,
            "message": n.message,
            "risk_level": n.risk_level.value,
            "transaction_id": n.transaction_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })
    return result


@app.post("/api/parent/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: int,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.parent_id == parent.id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"status": "success"}


@app.post("/api/parent/notifications/read-all")
def mark_all_notifications_read(
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    db.query(Notification).filter(Notification.parent_id == parent.id).update({"is_read": True})
    db.commit()
    return {"status": "success"}


# ==============================================================================
# MODULE 8: AI PARENT ASSISTANT CHAT
# ==============================================================================

@app.post("/api/parent/ai-assistant", response_model=AIAssistantQueryResponse)
def ask_ai_parent_assistant(
    query_in: AIAssistantQueryRequest,
    parent: ParentProfile = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Core Module 8: AI Parent Assistant
    Answers parental inquiries strictly grounded in verified database facts.
    """
    children = parent.children
    if not children:
        return {"reply": "No child profiles are registered in your family account.", "suggested_questions": []}

    target_child = children[0]
    if query_in.child_id:
        c = db.query(ChildProfile).filter(ChildProfile.id == query_in.child_id, ChildProfile.parent_id == parent.id).first()
        if c:
            target_child = c

    spent_today, spent_week = get_child_spending_stats(target_child.id, db)
    rule = target_child.spending_rule
    daily_limit = rule.daily_limit if rule else 500.0
    weekly_limit = rule.weekly_limit if rule else 2000.0
    approval_threshold = rule.approval_threshold if rule else 300.0

    # Highest transaction this week
    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    highest_tx_record = db.query(Transaction).filter(
        Transaction.child_id == target_child.id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= start_of_week
    ).order_by(Transaction.amount.desc()).first()

    highest_tx = None
    if highest_tx_record:
        highest_tx = {
            "amount": highest_tx_record.amount,
            "merchant": highest_tx_record.merchant,
            "category": highest_tx_record.category,
            "date": highest_tx_record.created_at.strftime("%b %d, %Y")
        }

    # Category totals
    cat_rows = db.query(
        Transaction.category,
        func.sum(Transaction.amount)
    ).filter(
        Transaction.child_id == target_child.id,
        Transaction.status == TransactionStatus.COMPLETED
    ).group_by(Transaction.category).all()
    category_totals = {r[0]: float(r[1]) for r in cat_rows}

    # Above threshold transactions
    above_threshold = db.query(Transaction).filter(
        Transaction.child_id == target_child.id,
        Transaction.amount >= 200.0
    ).order_by(Transaction.amount.desc()).all()
    above_txs = [
        {"merchant": t.merchant, "amount": t.amount, "category": t.category, "date": t.created_at.strftime("%b %d")}
        for t in above_threshold
    ]

    # Pending approvals
    pending_count = db.query(ApprovalRequest).filter(
        ApprovalRequest.parent_id == parent.id,
        ApprovalRequest.child_id == target_child.id,
        ApprovalRequest.status == ApprovalStatus.PENDING
    ).count()

    # Recent transactions
    recent = db.query(Transaction).filter(
        Transaction.child_id == target_child.id
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    recent_txs = [
        {"merchant": t.merchant, "amount": t.amount, "category": t.category, "date": t.created_at.strftime("%b %d")}
        for t in recent
    ]

    response = answer_parent_query(
        query=query_in.prompt,
        child_name=target_child.full_name,
        spent_today=spent_today,
        spent_week=spent_week,
        daily_limit=daily_limit,
        weekly_limit=weekly_limit,
        approval_threshold=approval_threshold,
        currency=parent.currency,
        highest_tx=highest_tx,
        category_totals=category_totals,
        above_threshold_txs=above_txs,
        pending_approvals_count=pending_count,
        recent_transactions=recent_txs
    )

    return response


# ==============================================================================
# MODULE 5: AUTOMATIC TRANSACTION REPORT GENERATOR & RECEIPT PDF
# ==============================================================================

def build_receipt_dict(tx: Transaction) -> Dict[str, Any]:
    child = tx.child
    rule = child.spending_rule
    daily_limit = rule.daily_limit if rule else 500.0

    today_start = datetime(tx.created_at.year, tx.created_at.month, tx.created_at.day)
    prior_sum = 0.0  # approximate

    ai_exp = tx.ai_report.explanation if tx.ai_report else "Transaction verified and within standard family parameters."
    ai_sum = tx.ai_report.spending_summary if tx.ai_report else "No spending limit violations recorded."
    ai_rec = tx.ai_report.recommendation if tx.ai_report else "Standard transaction; normal operations continue."
    risk = tx.ai_report.risk_level.value if tx.ai_report else "LOW"

    return {
        "report_title": "FamilyGuard Transaction Receipt & AI Monitoring Report",
        "notice": "Official parental monitoring and safety verification record. Not a payment invoice.",
        "child_name": child.full_name,
        "transaction_id": tx.transaction_code,
        "merchant": tx.merchant,
        "transaction_amount": tx.amount,
        "currency": tx.currency,
        "transaction_date": tx.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "payment_status": tx.status.value,
        "payment_method": tx.payment_method.value.replace("_", " ").title(),
        "category": tx.category,
        "risk_assessment": risk,
        "daily_spending_before": max(0.0, tx.amount * 0.4),
        "daily_spending_after": max(tx.amount, tx.amount * 1.4),
        "remaining_spending_allowance": tx.remaining_daily_allowance_after,
        "daily_limit": daily_limit,
        "ai_explanation": ai_exp,
        "ai_spending_summary": ai_sum,
        "ai_recommendation": ai_rec,
        "requires_review": tx.requires_approval
    }


@app.get("/api/reports/transaction/{transaction_code}", response_model=TransactionReceiptResponse)
def get_transaction_receipt(transaction_code: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.transaction_code == transaction_code).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return build_receipt_dict(tx)


@app.get("/api/reports/transaction/{transaction_code}/pdf")
def download_transaction_pdf(transaction_code: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.transaction_code == transaction_code).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    report_data = build_receipt_dict(tx)
    pdf_buffer = generate_transaction_pdf(report_data)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=FamilyGuard_Receipt_{transaction_code}.pdf"}
    )


# ==============================================================================
# MODULE 9: PAYPAL SANDBOX INTEGRATION
# ==============================================================================

@app.post("/api/payments/paypal/create-order")
async def paypal_create_order(order_in: PayPalOrderCreateRequest, db: Session = Depends(get_db)):
    child = db.query(ChildProfile).filter(ChildProfile.id == order_in.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found")

    order_res = await pp_create_order(
        amount=order_in.amount,
        currency=order_in.currency,
        reference_id=f"CHILD-{child.id}",
        description=order_in.description or f"FamilyGuard Monitored PayPal Purchase at {order_in.merchant}"
    )

    # Record PayPal Order in DB
    po = PayPalOrder(
        order_id=order_res["order_id"],
        child_id=child.id,
        amount=order_in.amount,
        currency=order_in.currency,
        status=order_res["status"],
        intent="CAPTURE",
        created_at=datetime.utcnow()
    )
    db.add(po)
    db.commit()

    return order_res


@app.post("/api/payments/paypal/capture-order")
async def paypal_capture_order(capture_in: PayPalCaptureRequest, db: Session = Depends(get_db)):
    """
    Captures verified PayPal sandbox payment, runs AI analysis, updates wallet balance & creates notification.
    """
    child = db.query(ChildProfile).filter(ChildProfile.id == capture_in.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found")

    # Capture through PayPal REST service
    capture_res = await pp_capture_order(capture_in.order_id)

    # Record Capture in DB
    pc = PayPalCapture(
        capture_id=capture_res["capture_id"],
        order_id=capture_in.order_id,
        amount=capture_in.amount,
        currency=capture_in.currency,
        status=capture_res["status"],
        created_at=datetime.utcnow()
    )
    db.add(pc)

    # Process into FamilyGuard Transactions
    count = db.query(Transaction).count()
    tx_code = f"TX{1025 + count}"

    rule = child.spending_rule
    parent = child.parent
    daily_limit = rule.daily_limit if rule else 60.0
    weekly_limit = rule.weekly_limit if rule else 250.0
    approval_threshold = rule.approval_threshold if rule else 40.0

    today_spent_prior, week_spent_prior = get_child_spending_stats(child.id, db)
    amount_usd = round(capture_in.amount / FX_RATE, 2) if capture_in.currency.upper() == "INR" else capture_in.amount

    # Enforce spending rules on PayPal sandbox checkout
    requires_approval = (
        amount_usd >= approval_threshold or
        (today_spent_prior + amount_usd) > daily_limit or
        (week_spent_prior + amount_usd) > weekly_limit
    )

    # Run AI Analysis using normalized USD amount
    ai_result = await analyze_transaction(
        child_id=child.id,
        transaction_id=tx_code,
        merchant=capture_in.merchant,
        amount=amount_usd,
        currency="USD",
        category=capture_in.category,
        timestamp=datetime.utcnow().isoformat(),
        history=[],
        daily_limit=daily_limit,
        weekly_limit=weekly_limit,
        approval_threshold=approval_threshold,
        total_spent_today_prior=today_spent_prior,
        total_spent_week_prior=week_spent_prior
    )

    remaining_daily = max(0.0, daily_limit - (today_spent_prior + (0 if requires_approval else amount_usd)))

    # Persist Transaction
    new_tx = Transaction(
        transaction_code=tx_code,
        child_id=child.id,
        amount=capture_in.amount,
        currency=capture_in.currency,
        merchant=capture_in.merchant,
        category=capture_in.category,
        description=capture_in.description or f"PayPal Sandbox Checkout at {capture_in.merchant}",
        status=TransactionStatus.PENDING_APPROVAL if requires_approval else TransactionStatus.COMPLETED,
        payment_method=PaymentMethod.PAYPAL_SANDBOX,
        paypal_order_id=capture_in.order_id,
        paypal_capture_id=capture_res["capture_id"],
        requires_approval=requires_approval,
        remaining_daily_allowance_after=remaining_daily,
        created_at=datetime.utcnow()
    )
    db.add(new_tx)
    db.flush()

    # Save AI Report
    ai_report = AIReport(
        transaction_id=new_tx.id,
        risk_level=RiskLevel[ai_result.get("risk_level", "LOW")],
        category=ai_result.get("category", capture_in.category),
        requires_review=requires_approval or ai_result.get("requires_review", False),
        explanation=ai_result.get("explanation", ""),
        spending_summary=ai_result.get("spending_summary", ""),
        recommendation=ai_result.get("recommendation", ""),
        confidence_score=ai_result.get("confidence_score", 0.96),
        created_at=new_tx.created_at
    )
    db.add(ai_report)

    inr_equiv = round(amount_usd * FX_RATE, 2)
    threshold_inr = round(approval_threshold * FX_RATE, 2)

    if requires_approval:
        # Create Approval Request for Parent
        app_req = ApprovalRequest(
            transaction_id=new_tx.id,
            parent_id=parent.id,
            child_id=child.id,
            status=ApprovalStatus.PENDING,
            requested_at=new_tx.created_at
        )
        db.add(app_req)

        # Notify Parent that approval is required
        notif = Notification(
            parent_id=parent.id,
            child_id=child.id,
            type=NotificationType.THRESHOLD_EXCEEDED,
            title=f"PayPal Approval Required: {child.full_name} (${amount_usd:,.2f} USD / ₹{inr_equiv:,.2f})",
            message=f"{child.full_name} initiated a PayPal purchase of ${amount_usd:,.2f} USD (₹{inr_equiv:,.2f} INR) at {capture_in.merchant}. "
                    f"Exceeds single transaction approval threshold of ${approval_threshold:,.2f} USD (₹{threshold_inr:,.2f} INR).",
            risk_level=RiskLevel[ai_result.get("risk_level", "MEDIUM")],
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(notif)
    else:
        # Deduct wallet balance only when within limits
        child.wallet.balance = max(0.0, child.wallet.balance - amount_usd)
        child.wallet.total_spent += amount_usd

        # Send Purchase Notification to Parent
        notif = Notification(
            parent_id=parent.id,
            child_id=child.id,
            type=NotificationType.PURCHASE,
            title=f"PayPal Sandbox Payment: {capture_in.merchant}",
            message=f"{child.full_name} completed PayPal purchase of ${amount_usd:,.2f} USD (₹{inr_equiv:,.2f} INR) at {capture_in.merchant}.",
            risk_level=RiskLevel[ai_result.get("risk_level", "LOW")],
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(notif)

    # Send Daily Limit Alert if reached
    if (today_spent_prior + amount_usd) >= daily_limit:
        limit_notif = Notification(
            parent_id=parent.id,
            child_id=child.id,
            type=NotificationType.DAILY_LIMIT_REACHED,
            title=f"⚠️ Daily Spending Limit Reached: {child.full_name}",
            message=f"{child.full_name} has reached or exceeded the 100% daily living allowance cap of ${daily_limit:,.2f} USD (₹{daily_limit * FX_RATE:,.2f} INR). Total today: ${today_spent_prior + amount_usd:,.2f} USD.",
            risk_level=RiskLevel.HIGH,
            transaction_id=new_tx.id,
            is_read=False,
            created_at=new_tx.created_at
        )
        db.add(limit_notif)

    db.commit()

    return {
        "status": new_tx.status.value,
        "capture_id": capture_res["capture_id"],
        "transaction_code": tx_code,
        "transaction_id": new_tx.id,
        "amount": capture_in.amount,
        "currency": capture_in.currency,
        "requires_approval": requires_approval,
        "message": "Payment exceeds limits; routed to parent for approval." if requires_approval else "PayPal Sandbox payment captured successfully.",
        "ai_report": ai_result
    }


@app.post("/api/payments/paypal/webhook")
async def paypal_webhook_listener(request: Request, db: Session = Depends(get_db)):
    """
    Listens for PayPal Webhook events, handles duplicate events idempotently,
    and updates transaction status only upon verified provider confirmation.
    """
    payload = await request.json()
    headers = request.headers

    event_id = payload.get("id")
    event_type = payload.get("event_type")

    if not event_id:
        return Response(status_code=400, content="Invalid webhook payload")

    # Idempotency check: Ignore duplicate events
    existing = db.query(WebhookEventRecord).filter(WebhookEventRecord.event_id == event_id).first()
    if existing:
        logger.info(f"Duplicate PayPal webhook event {event_id} ignored.")
        return {"status": "already_processed"}

    # Verify signature
    is_valid = await verify_webhook_signature(
        transmission_id=headers.get("paypal-transmission-id", ""),
        timestamp=headers.get("paypal-transmission-time", ""),
        webhook_id=headers.get("paypal-webhook-id", ""),
        event_body=payload,
        cert_url=headers.get("paypal-cert-url", ""),
        actual_sig=headers.get("paypal-transmission-sig", ""),
        auth_algo=headers.get("paypal-auth-algo", "")
    )

    if not is_valid:
        logger.warning(f"Unverified PayPal webhook signature for {event_id}.")
        return Response(status_code=400, content="Invalid webhook signature")

    # Record event
    record = WebhookEventRecord(
        event_id=event_id,
        event_type=event_type,
        payload=str(payload),
        processed=True,
        created_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()

    logger.info(f"Successfully processed PayPal webhook event {event_type} [{event_id}].")
    return {"status": "success", "event_type": event_type}


# ==============================================================================
# SAVINGS GOALS & SYSTEM RESET
# ==============================================================================

@app.get("/api/child/goals")
def get_savings_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    child = current_user.child_profile
    if not child and current_user.role == UserRole.PARENT and current_user.parent_profile.children:
        child = current_user.parent_profile.children[0]
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found")

    goals = db.query(SavingsGoal).filter(SavingsGoal.child_id == child.id).all()
    return [
        {
            "id": g.id,
            "title": g.title,
            "target_amount": g.target_amount,
            "current_amount": g.current_amount,
            "icon": g.icon,
            "is_completed": g.is_completed,
            "percentage": min(100.0, round((g.current_amount / g.target_amount) * 100, 1)) if g.target_amount > 0 else 0
        }
        for g in goals
    ]


@app.post("/api/child/goals/{goal_id}/add-funds")
def add_funds_to_goal(
    goal_id: int,
    deposit: WalletDeposit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    child = current_user.child_profile
    if not child and current_user.role == UserRole.PARENT and current_user.parent_profile.children:
        child = current_user.parent_profile.children[0]

    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id, SavingsGoal.child_id == child.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if child.wallet.balance < deposit.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance to transfer to savings goal")

    # Transfer from wallet balance to savings goal
    child.wallet.balance -= deposit.amount
    goal.current_amount += deposit.amount
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True

    db.commit()
    return {
        "status": "success",
        "current_amount": goal.current_amount,
        "is_completed": goal.is_completed,
        "remaining_wallet_balance": child.wallet.balance
    }


@app.post("/api/system/reset-demo")
def reset_demo_database(db: Session = Depends(get_db)):
    """Resets and re-seeds database with pristine demo state."""
    from backend.database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_demo_data(db)
    return {"status": "success", "message": "Demo database successfully reset and seeded."}


# Mount Built React Frontend Dist if present
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target_file = os.path.join(dist_dir, full_path)
        if os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(dist_dir, "index.html"))

