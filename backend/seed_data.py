from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import (
    User, UserRole, ParentProfile, ChildProfile, WalletAccount,
    SpendingRule, Transaction, AIReport, ApprovalRequest,
    Notification, NotificationType, RiskLevel, TransactionStatus,
    PaymentMethod, ApprovalStatus, SavingsGoal
)
from backend.auth import get_password_hash

FX_RATE = 85.0  # 1 USD = 85.00 INR


def seed_demo_data(db: Session):
    """
    Seeds initial synthetic demonstration data for the Study-Abroad Cross-Border scenario:
    - Parent: Demo Parent (India, Mumbai) - Operates in INR (₹)
    - Child: Arjun (Studying abroad in US) - Operates in USD ($)
    - Initial simulated balance: $250.00 USD (~₹21,250 INR)
    - Daily limit: $60.00 USD (~₹5,100 INR)
    - Weekly limit: $250.00 USD (~₹21,250 INR)
    - Approval threshold: $40.00 USD (~₹3,400 INR)
    """
    # Check if already seeded
    existing_parent = db.query(User).filter(User.email == "parent@familyguard.demo").first()
    if existing_parent:
        return

    # 1. Create Parent User & Profile (Indian Parent)
    parent_user = User(
        email="parent@familyguard.demo",
        hashed_password=get_password_hash("Password123!"),
        full_name="Demo Parent",
        role=UserRole.PARENT,
        is_active=True
    )
    db.add(parent_user)
    db.flush()

    parent_profile = ParentProfile(
        user_id=parent_user.id,
        phone="+91 98765 43210",
        currency="INR"
    )
    db.add(parent_profile)
    db.flush()

    # 2. Create Child User & Profile (Arjun - Student Abroad)
    child_user = User(
        email="arjun@familyguard.demo",
        hashed_password=get_password_hash("Password123!"),
        full_name="Arjun",
        role=UserRole.CHILD,
        is_active=True
    )
    db.add(child_user)
    db.flush()

    child_profile = ChildProfile(
        user_id=child_user.id,
        parent_id=parent_profile.id,
        full_name="Arjun",
        age=19,
        avatar="Arjun",
        is_active=True
    )
    db.add(child_profile)
    db.flush()

    # 3. Create Child Wallet ($250.00 USD initial study allowance)
    wallet = WalletAccount(
        child_id=child_profile.id,
        currency="USD",
        balance=250.0,
        total_spent=53.5,
        total_deposited=303.5
    )
    db.add(wallet)

    # 4. Create Spending Rules in USD (Daily: $60.00, Weekly: $250.00, Threshold: $40.00)
    spending_rule = SpendingRule(
        child_id=child_profile.id,
        daily_limit=60.0,
        weekly_limit=250.0,
        approval_threshold=40.0,
        allowed_categories="Education,Books,Food & Snacks,Entertainment,Gaming,Shopping,Transport,Dorm Essentials",
        blocked_merchants="Adult Content,Cryptocurrency Exchange,Online Betting",
        is_active=True
    )
    db.add(spending_rule)

    # 5. Create Savings Goals in USD
    goals = [
        SavingsGoal(
            child_id=child_profile.id,
            title="MacBook Pro Study Fund",
            target_amount=1200.0,
            current_amount=450.0,
            icon="Laptop",
            target_date=datetime.utcnow() + timedelta(days=90),
            is_completed=False
        ),
        SavingsGoal(
            child_id=child_profile.id,
            title="Fall Semester Break Travel",
            target_amount=500.0,
            current_amount=200.0,
            icon="Plane",
            target_date=datetime.utcnow() + timedelta(days=45),
            is_completed=False
        ),
        SavingsGoal(
            child_id=child_profile.id,
            title="Campus Commuter Bike",
            target_amount=250.0,
            current_amount=110.0,
            icon="Bike",
            target_date=datetime.utcnow() + timedelta(days=20),
            is_completed=False
        )
    ]
    db.add_all(goals)

    # 6. Create Historical Pre-Seeded Transactions (in USD with INR conversion context)
    t1 = Transaction(
        transaction_code="TX1021",
        child_id=child_profile.id,
        amount=18.50,
        currency="USD",
        merchant="Campus Dining & Groceries",
        category="Food & Snacks",
        description="Weekly dorm groceries and healthy meal plan snack",
        status=TransactionStatus.COMPLETED,
        payment_method=PaymentMethod.PAYPAL_SANDBOX,
        requires_approval=False,
        remaining_daily_allowance_after=41.50,
        created_at=datetime.utcnow() - timedelta(days=2, hours=3)
    )
    db.add(t1)
    db.flush()

    ai_t1 = AIReport(
        transaction_id=t1.id,
        risk_level=RiskLevel.LOW,
        category="Food & Snacks",
        requires_review=False,
        explanation=f"Routine campus meal expense of $18.50 USD (₹{18.50 * FX_RATE:,.2f} INR). Safely within daily foreign living allowance.",
        spending_summary="Arjun consumed 30.8% of daily allowance ($18.50 / $60.00 USD). No anomalies identified.",
        recommendation="Standard approved student living expense. No parental action needed.",
        confidence_score=0.98,
        created_at=t1.created_at
    )
    db.add(ai_t1)

    t2 = Transaction(
        transaction_code="TX1022",
        child_id=child_profile.id,
        amount=35.00,
        currency="USD",
        merchant="MIT Press & Academic Bookstore",
        category="Education",
        description="Computer Science Algorithms & Data Structures textbook",
        status=TransactionStatus.COMPLETED,
        payment_method=PaymentMethod.PAYPAL_SANDBOX,
        requires_approval=False,
        remaining_daily_allowance_after=25.00,
        created_at=datetime.utcnow() - timedelta(days=1, hours=5)
    )
    db.add(t2)
    db.flush()

    ai_t2 = AIReport(
        transaction_id=t2.id,
        risk_level=RiskLevel.LOW,
        category="Education",
        requires_review=False,
        explanation=f"Essential university study material of $35.00 USD (₹{35.00 * FX_RATE:,.2f} INR) purchased from verified academic bookstore.",
        spending_summary="Arjun used 58.3% of daily study allowance. Cumulative weekly usage remains well under 25%.",
        recommendation="Encouraged academic expenditure. Transaction logged cleanly in PayPal Sandbox audit vault.",
        confidence_score=0.99,
        created_at=t2.created_at
    )
    db.add(ai_t2)

    # 7. Create Pre-Seeded Parent Notifications (with dual currency)
    n1 = Notification(
        parent_id=parent_profile.id,
        child_id=child_profile.id,
        type=NotificationType.PURCHASE,
        title="PayPal Verified: MIT Press & Academic Bookstore",
        message=f"Arjun spent $35.00 USD (₹{35.00 * FX_RATE:,.2f} INR) on academic textbook at MIT Press.",
        risk_level=RiskLevel.LOW,
        transaction_id=t2.id,
        is_read=False,
        created_at=datetime.utcnow() - timedelta(days=1, hours=5)
    )
    n2 = Notification(
        parent_id=parent_profile.id,
        child_id=child_profile.id,
        type=NotificationType.PURCHASE,
        title="PayPal Verified: Campus Dining & Groceries",
        message=f"Arjun spent $18.50 USD (₹{18.50 * FX_RATE:,.2f} INR) at Campus Dining & Groceries.",
        risk_level=RiskLevel.LOW,
        transaction_id=t1.id,
        is_read=True,
        created_at=datetime.utcnow() - timedelta(days=2, hours=3)
    )
    db.add_all([n1, n2])

    db.commit()
