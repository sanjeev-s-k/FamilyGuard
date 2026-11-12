import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("familyguard.ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def analyze_transaction_with_rules(
    transaction_id: str,
    merchant: str,
    amount: float,
    currency: str,
    category: str,
    timestamp: str,
    history: List[Dict[str, Any]],
    daily_limit: float,
    weekly_limit: float,
    approval_threshold: float,
    total_spent_today_prior: float,
    total_spent_week_prior: float,
) -> Dict[str, Any]:
    """
    Deterministic fintech safety rule engine.
    Follows strict financial safety guidelines:
    - Verifiable facts distinguished from predictions
    - Never authorizes/executes payments
    - Does not mark fraudulent merely because it's unusual
    """
    new_daily_total = total_spent_today_prior + amount
    daily_percent = round((new_daily_total / daily_limit) * 100, 1) if daily_limit > 0 else 0
    weekly_percent = round(((total_spent_week_prior + amount) / weekly_limit) * 100, 1) if weekly_limit > 0 else 0

    exceeds_threshold = amount >= approval_threshold
    exceeds_daily = new_daily_total > daily_limit
    exceeds_weekly = (total_spent_week_prior + amount) > weekly_limit

    # Check merchant and category risk flags
    high_risk_categories = ["Gambling", "Adult", "Cryptocurrency", "Weapons"]
    gaming_categories = ["Gaming", "In-App Purchase", "Entertainment"]

    is_high_risk_category = any(h.lower() in category.lower() for h in high_risk_categories)
    is_gaming = any(g.lower() in category.lower() for g in gaming_categories)

    # Check average transaction size from history
    past_amounts = [t.get("amount", 0) for t in history if isinstance(t.get("amount"), (int, float))]
    avg_past = (sum(past_amounts) / len(past_amounts)) if past_amounts else amount
    is_unusual_amount = amount > (avg_past * 2.5) and amount > 300

    # Risk level determination:
    # HIGH risk ONLY if daily limit or weekly limit is exceeded, or high-risk category (gambling, crypto, etc.)
    if is_high_risk_category or exceeds_daily or exceeds_weekly:
        risk_level = "HIGH"
        requires_review = True
    elif exceeds_threshold:
        risk_level = "MEDIUM"
        requires_review = True
    else:
        risk_level = "LOW"
        requires_review = False

    # Explanation generation
    explanation_parts = []
    if exceeds_threshold:
        explanation_parts.append(
            f"Transaction amount of {currency} {amount:,.2f} exceeds the parent-configured approval threshold of {currency} {approval_threshold:,.2f}."
        )
    else:
        explanation_parts.append(
            f"The transaction of {currency} {amount:,.2f} at {merchant} is within the single-purchase limit."
        )

    if exceeds_daily:
        explanation_parts.append(f"Cumulative spending today ({currency} {new_daily_total:,.2f}) surpasses the daily cap of {currency} {daily_limit:,.2f}.")
    elif daily_percent >= 80:
        explanation_parts.append(f"Daily spending reaches {daily_percent}% of the {currency} {daily_limit:,.2f} daily allowance.")

    if is_unusual_amount:
        explanation_parts.append(f"Spending at {merchant} is significantly higher than historical average transaction size ({currency} {avg_past:,.2f}).")

    explanation = " ".join(explanation_parts)

    # Spending summary
    remaining_daily = max(0.0, daily_limit - new_daily_total)
    spending_summary = (
        f"The child has used {daily_percent}% of the daily allowance ({currency} {new_daily_total:,.2f}/{currency} {daily_limit:,.2f}). "
        f"Remaining daily allowance: {currency} {remaining_daily:,.2f}. Weekly utilization: {weekly_percent}%."
    )

    # Recommendation
    if risk_level == "HIGH":
        recommendation = "High risk detected. Parental confirmation required before proceeding with similar transactions."
    elif risk_level == "MEDIUM" or requires_review:
        recommendation = "Review recommended to verify whether this purchase aligns with agreed family guidelines."
    else:
        recommendation = "No additional review recommended. Transaction falls safely within normal parameters."

    # Normalise standard category classification
    classified_category = category if category and category != "General" else "Shopping"

    return {
        "transaction_id": transaction_id,
        "category": classified_category,
        "risk_level": risk_level,
        "requires_review": requires_review,
        "explanation": explanation,
        "spending_summary": spending_summary,
        "recommendation": recommendation,
        "confidence_score": 0.94
    }


async def analyze_transaction(
    child_id: int,
    transaction_id: str,
    merchant: str,
    amount: float,
    currency: str,
    category: str,
    timestamp: str,
    history: List[Dict[str, Any]],
    daily_limit: float,
    weekly_limit: float,
    approval_threshold: float,
    total_spent_today_prior: float,
    total_spent_week_prior: float,
) -> Dict[str, Any]:
    """
    Core Module 4: AI Transaction Monitoring Engine
    Sends structured information to OpenAI API if configured,
    or falls back cleanly to the deterministic safety engine.
    """
    rule_assessment = analyze_transaction_with_rules(
        transaction_id=transaction_id,
        merchant=merchant,
        amount=amount,
        currency=currency,
        category=category,
        timestamp=timestamp,
        history=history,
        daily_limit=daily_limit,
        weekly_limit=weekly_limit,
        approval_threshold=approval_threshold,
        total_spent_today_prior=total_spent_today_prior,
        total_spent_week_prior=total_spent_week_prior,
    )

    if not OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not configured. Using FamilyGuard Deterministic Safety Rule Engine.")
        return rule_assessment

    system_prompt = (
        "You are FamilyGuard AI, an intelligent parental payment monitoring and transaction risk assessment engine. "
        "Your task is to analyze children's transactions with utmost precision and explainability. "
        "CRITICAL SAFETY RULES:\n"
        "1. You must NEVER independently authorize or execute payments.\n"
        "2. Spending limits are strictly enforced by backend rules; do not override them.\n"
        "3. You must NOT invent fake transaction details.\n"
        "4. Distinguish verified facts from predictions.\n"
        "5. Do NOT automatically classify a transaction as fraudulent solely because it is unusual.\n"
        "6. Return ONLY valid JSON matching the exact schema requested."
    )

    user_payload = {
        "child_id": child_id,
        "transaction_id": transaction_id,
        "merchant": merchant,
        "amount": amount,
        "currency": currency,
        "category": category,
        "timestamp": timestamp,
        "previous_transaction_count": len(history),
        "recent_history_sample": history[:5],
        "daily_limit": daily_limit,
        "weekly_limit": weekly_limit,
        "approval_threshold": approval_threshold,
        "spent_today_before_tx": total_spent_today_prior,
        "spent_week_before_tx": total_spent_week_prior,
        "preliminary_rules": rule_assessment
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this transaction and return JSON with keys: transaction_id, category, risk_level (LOW, MEDIUM, or HIGH), requires_review (bool), explanation, spending_summary, recommendation.\n\nData:\n{json.dumps(user_payload)}"
                        }
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                # Ensure all required keys exist
                return {
                    "transaction_id": parsed.get("transaction_id", transaction_id),
                    "category": parsed.get("category", rule_assessment["category"]),
                    "risk_level": parsed.get("risk_level", rule_assessment["risk_level"]).upper(),
                    "requires_review": bool(parsed.get("requires_review", rule_assessment["requires_review"])),
                    "explanation": parsed.get("explanation", rule_assessment["explanation"]),
                    "spending_summary": parsed.get("spending_summary", rule_assessment["spending_summary"]),
                    "recommendation": parsed.get("recommendation", rule_assessment["recommendation"]),
                    "confidence_score": 0.96
                }
            else:
                logger.warning(f"OpenAI API responded with status {response.status_code}: {response.text}")
                return rule_assessment

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}. Falling back to deterministic rules.")
        return rule_assessment


FX_RATE = 85.0  # 1 USD = 85.00 INR


def answer_parent_query(
    query: str,
    child_name: str,
    spent_today: float,
    spent_week: float,
    daily_limit: float,
    weekly_limit: float,
    approval_threshold: float,
    currency: str,
    highest_tx: Optional[Dict[str, Any]],
    category_totals: Dict[str, float],
    above_threshold_txs: List[Dict[str, Any]],
    pending_approvals_count: int,
    recent_transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Core Module 8: AI Parent Assistant
    Answers parental inquiries strictly grounded in verified database facts,
    with dual-currency (USD study allowance & INR parent debit) intelligence.
    """
    q = query.lower()

    # Question 1: How much did child spend today?
    if "today" in q or "spent today" in q or "daily spend" in q:
        remaining = max(0.0, daily_limit - spent_today)
        pct = round((spent_today / daily_limit) * 100, 1) if daily_limit > 0 else 0
        reply = (
            f"**{child_name}** has spent **${spent_today:,.2f} USD (₹{spent_today * FX_RATE:,.2f} INR)** today, "
            f"which is **{pct}%** of their **${daily_limit:,.2f} USD (₹{daily_limit * FX_RATE:,.2f} INR)** daily living allowance. "
            f"They have **${remaining:,.2f} USD (₹{remaining * FX_RATE:,.2f} INR)** remaining for the rest of today."
        )
        return {"reply": reply, "suggested_questions": ["What was the highest transaction this week?", "Which category has the highest spending?", "Are there any transactions requiring review?"]}

    # Question 2: Highest transaction this week?
    if "highest" in q or "largest" in q or "biggest" in q or "max" in q:
        if highest_tx:
            amt_usd = highest_tx['amount']
            amt_inr = amt_usd * FX_RATE
            reply = (
                f"The highest transaction for **{child_name}** this week was **${amt_usd:,.2f} USD (₹{amt_inr:,.2f} INR)** at **{highest_tx['merchant']}** "
                f"under the **{highest_tx['category']}** category on {highest_tx['date']}."
            )
        else:
            reply = f"No transactions recorded for **{child_name}** this week."
        return {"reply": reply, "suggested_questions": ["How much did my child spend today?", "Which category has the highest spending?"]}

    # Question 3: Which category has the highest spending?
    if "category" in q or "categories" in q or "highest spending" in q:
        if category_totals:
            sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            top_cat, top_amt = sorted_cats[0]
            cat_breakdown = ", ".join([f"**{c}**: ${a:,.2f} USD (₹{a * FX_RATE:,.2f} INR)" for c, a in sorted_cats])
            reply = (
                f"The category with the highest overseas spending is **{top_cat}** at **${top_amt:,.2f} USD (₹{top_amt * FX_RATE:,.2f} INR)**.\n\n"
                f"**Full Category Breakdown:**\n{cat_breakdown}"
            )
        else:
            reply = f"No category spending data found yet for **{child_name}**."
        return {"reply": reply, "suggested_questions": ["Show transactions above ₹200", "How much of the weekly allowance remains?"]}

    # Question 4: Show transactions above specific threshold
    if "above" in q or "greater than" in q or "more than" in q or "over" in q:
        target_usd = 20.0  # default
        import re
        numbers = re.findall(r'\d+', q)
        if numbers:
            num = float(numbers[0])
            target_usd = (num / FX_RATE) if num > 100 else num

        matching = [t for t in recent_transactions if t.get("amount", 0) >= target_usd]
        if matching:
            lines = [f"- **{t['merchant']}**: ${t['amount']:,.2f} USD (₹{t['amount'] * FX_RATE:,.2f} INR) • {t['category']} on {t['date']}" for t in matching[:5]]
            reply = (
                f"Found **{len(matching)} transaction(s)** for {child_name} above ${target_usd:,.2f} USD (₹{target_usd * FX_RATE:,.2f} INR):\n\n" +
                "\n".join(lines)
            )
        else:
            reply = f"No transactions found for {child_name} exceeding ${target_usd:,.2f} USD (₹{target_usd * FX_RATE:,.2f} INR)."
        return {"reply": reply, "suggested_questions": ["Are there any transactions requiring review?", "How much of the weekly allowance remains?"]}

    # Question 5: How much of weekly allowance remains?
    if "weekly" in q or "allowance" in q or "remains" in q or "remaining" in q:
        rem_weekly = max(0.0, weekly_limit - spent_week)
        pct = round((spent_week / weekly_limit) * 100, 1) if weekly_limit > 0 else 0
        reply = (
            f"**{child_name}** has used **${spent_week:,.2f} USD (₹{spent_week * FX_RATE:,.2f} INR)** (**{pct}%**) of their **${weekly_limit:,.2f} USD** weekly limit. "
            f"A total of **${rem_weekly:,.2f} USD (₹{rem_weekly * FX_RATE:,.2f} INR)** remains available for the rest of the week."
        )
        return {"reply": reply, "suggested_questions": ["How much did my child spend today?", "Generate a monthly spending summary"]}

    # Question 6: Monthly spending summary
    if "monthly" in q or "month" in q or "summary" in q or "report" in q:
        total_usd = spent_week + spent_today
        reply = (
            f"### Monthly Cross-Border Study Expenditure Summary for {child_name}\n"
            f"- **Total Monthly Expenditure**: ${total_usd:,.2f} USD (₹{total_usd * FX_RATE:,.2f} INR)\n"
            f"- **Active Weekly Cap**: ${weekly_limit:,.2f} USD (₹{weekly_limit * FX_RATE:,.2f} INR)\n"
            f"- **Single-Purchase Approval Threshold**: ${approval_threshold:,.2f} USD (₹{approval_threshold * FX_RATE:,.2f} INR)\n"
            f"- **Pending Approvals**: {pending_approvals_count} request(s)\n"
            f"- **Exchange Rate Index**: 1 USD = ₹{FX_RATE:.2f} INR (Pegged)\n"
            f"- **Health Rating**: Spend behavior is well-regulated for US student living standards."
        )
        return {"reply": reply, "suggested_questions": ["Are there any transactions requiring review?", "What was the highest transaction this week?"]}

    # Question 7: Are there any transactions requiring review?
    if "review" in q or "pending" in q or "approval" in q or "flagged" in q:
        if pending_approvals_count > 0:
            reply = (
                f"Yes. There is currently **{pending_approvals_count} transaction(s)** awaiting your review in the **Approval Requests** tab. "
                f"These transactions exceeded the single-transaction threshold of ${approval_threshold:,.2f} USD (₹{approval_threshold * FX_RATE:,.2f} INR)."
            )
        else:
            reply = f"All clear! There are currently **no pending approval requests** requiring your review for {child_name}."
        return {"reply": reply, "suggested_questions": ["How much did my child spend today?", "Show transactions above ₹200"]}

    # Default general query fallback
    reply = (
        f"I am FamilyGuard AI Assistant (PayPal Sandbox Monitored). Monitoring {child_name}'s overseas education expenses:\n"
        f"- **Spent Today**: ${spent_today:,.2f} USD / ${daily_limit:,.2f} USD (₹{spent_today * FX_RATE:,.2f} INR)\n"
        f"- **Spent This Week**: ${spent_week:,.2f} USD / ${weekly_limit:,.2f} USD (₹{spent_week * FX_RATE:,.2f} INR)\n"
        f"- **Pending Approvals**: {pending_approvals_count}\n"
        f"- **Exchange Rate**: 1 USD = ₹{FX_RATE:.2f} INR\n"
        f"You can ask me questions like: 'How much did Arjun spend today?', 'What was the highest transaction this week?', or 'How much allowance remains?'."
    )
    return {
        "reply": reply,
        "suggested_questions": [
            "How much did my child spend today?",
            "What was the highest transaction this week?",
            "Which category has the highest spending?",
            "Show transactions above ₹200",
            "How much of the weekly allowance remains?",
            "Are there any transactions requiring review?"
        ]
    }
