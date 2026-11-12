"""
Explainable Context-Based Risk Scoring Engine
Calculates transparent numerical risk scores (0-100), maps them to configurable risk bands,
and produces granular factor breakdowns, natural language explanations, and actionable recommendations.
"""

from typing import Dict, Any, List, Tuple
from backend.models import RiskAssessment, RiskFactorExplanation
from backend.ml_engine import ml_classifier


class RiskScorer:
    """Computes explainable, context-aware risk scores."""

    def __init__(self, threshold_low: int = 30, threshold_med: int = 60, threshold_high: int = 80):
        self.threshold_low = threshold_low
        self.threshold_med = threshold_med
        self.threshold_high = threshold_high

    def calculate_risk(self, events: List[Dict[str, Any]], context: Dict[str, Any]) -> RiskAssessment:
        """
        Calculates context-driven risk score across an aggregate set of correlated events.
        """
        if not events:
            return RiskAssessment(
                overall_score=0,
                risk_level="LOW",
                confidence=1.0,
                reasons=["No security events detected in the evaluation window."],
                factor_breakdown=[],
                recommended_action="Normal state. No action required."
            )

        score = 0
        reasons = []
        breakdown: List[RiskFactorExplanation] = []

        # 1. Analyze Authentication Failures
        failed_events = [e for e in events if e.get("event_type") == "FAILED_LOGIN"]
        max_explicit_count = max([e.get("failed_attempt_count", 0) for e in events] or [0])
        total_failed_count = max(len(failed_events), max_explicit_count)

        # Check sequence: failed login -> successful login
        has_success_after_failure = bool(context.get("success_after_failures", False))
        login_events = [e for e in events if e.get("event_type") in ["FAILED_LOGIN", "SUCCESSFUL_LOGIN"]]
        for i in range(len(login_events) - 1):
            if login_events[i].get("event_type") == "FAILED_LOGIN" and login_events[i + 1].get("event_type") == "SUCCESSFUL_LOGIN":
                has_success_after_failure = True
                break

        if total_failed_count > 0:
            fail_points = min(25, total_failed_count * 4)
            score += fail_points
            reasons.append(f"Detected {total_failed_count} failed authentication attempt(s).")
            breakdown.append(RiskFactorExplanation(
                factor_name="Authentication Failures",
                points_contributed=fail_points,
                description=f"Recorded {total_failed_count} failed login attempts prior to authorization.",
                severity="WARNING" if total_failed_count >= 5 else "INFO"
            ))

        if has_success_after_failure and total_failed_count >= 4:
            pts = 20
            score += pts
            reasons.append(f"Successful authentication occurred immediately following {total_failed_count} repeated failed attempts (potential brute-force or credential guessing).")
            breakdown.append(RiskFactorExplanation(
                factor_name="Success After Repeated Failures",
                points_contributed=pts,
                description=f"User successfully authenticated after {total_failed_count} consecutive failed attempts.",
                severity="WARNING"
            ))

        # 2. Unusual Location Analysis
        unusual_locations = set()
        for e in events:
            if e.get("unusual_location") or context.get("is_unusual_location"):
                unusual_locations.add(e.get("location"))

        if unusual_locations:
            pts = 18
            score += pts
            loc_str = ", ".join(unusual_locations)
            reasons.append(f"Authentication originating from unusual / unauthorized regional location: {loc_str}.")
            breakdown.append(RiskFactorExplanation(
                factor_name="Unusual Location",
                points_contributed=pts,
                description=f"Log activity occurred in {loc_str}, outside the user's registered home baseline.",
                severity="WARNING"
            ))

        # 3. Unknown Device Analysis
        unknown_devices = set()
        for e in events:
            if e.get("unknown_device") or context.get("is_unknown_device"):
                unknown_devices.add(e.get("device_id"))

        if unknown_devices:
            pts = 15
            score += pts
            dev_str = ", ".join(unknown_devices)
            reasons.append(f"Access initiated from unregistered / unknown device hardware: {dev_str}.")
            breakdown.append(RiskFactorExplanation(
                factor_name="Unknown Device",
                points_contributed=pts,
                description=f"Device {dev_str} is not present in organization's trusted device registry.",
                severity="WARNING"
            ))

        # Compound Anomaly: Unusual Location + Unknown Device
        if unusual_locations and unknown_devices:
            pts = 15
            score += pts
            reasons.append("High-risk compound anomaly: Unregistered hardware operating from unauthorized regional location.")
            breakdown.append(RiskFactorExplanation(
                factor_name="Cross-Location Unregistered Hardware Anomaly",
                points_contributed=pts,
                description="Combination of unregistered device and foreign regional access point indicates probable credential stuffing / intrusion.",
                severity="CRITICAL"
            ))

        # 4. Unusual Access Time
        unusual_times = [e for e in events if e.get("unusual_time")]
        if unusual_times:
            pts = 10
            score += pts
            reasons.append("Activity observed during non-standard operational hours (off-shift / 02:00 - 05:00 UTC).")
            breakdown.append(RiskFactorExplanation(
                factor_name="Unusual Time",
                points_contributed=pts,
                description="Events timestamped outside designated personnel shift window.",
                severity="INFO"
            ))

        # 5. ⭐ Cross-Location Threat Correlation Points
        unique_locations = set(e.get("location") for e in events if e.get("location"))
        cross_loc_cnt = max(len(unique_locations), context.get("cross_location_count", 1))
        if cross_loc_cnt >= 3:
            pts = 30
            score += pts
            reasons.append(f"Multi-regional cross-location pattern: Activity correlated across {cross_loc_cnt} locations ({', '.join(unique_locations) or 'multi-region'}) within compressed time window.")
            breakdown.append(RiskFactorExplanation(
                factor_name="⭐ Cross-Location Threat Correlation (3+ Regions)",
                points_contributed=pts,
                description=f"Suspicious activity chained across {cross_loc_cnt} regional endpoints simultaneously.",
                severity="CRITICAL"
            ))
        elif cross_loc_cnt == 2:
            pts = 15
            score += pts
            reasons.append(f"Cross-location activity correlated between {', '.join(unique_locations) or '2 regional sectors'}.")
            breakdown.append(RiskFactorExplanation(
                factor_name="⭐ Cross-Location Threat Correlation (2 Regions)",
                points_contributed=pts,
                description="Correlated session hopping between 2 distinct regional data centers.",
                severity="WARNING"
            ))

        # 6. Impossible Travel Velocity
        if context.get("impossible_travel"):
            pts = 25
            score += pts
            details = context.get("travel_details", {})
            spd = details.get("calculated_speed_kmh", "excessive")
            from_loc = details.get("from_location", "Region A")
            to_loc = details.get("to_location", "Region B")
            time_m = details.get("time_diff_minutes", 10)
            reasons.append(f"Impossible Travel Alert: User moved from {from_loc} to {to_loc} in {time_m} mins ({spd} km/h required).")
            breakdown.append(RiskFactorExplanation(
                factor_name="Impossible Travel Velocity",
                points_contributed=pts,
                description=f"Physically impossible relocation from {from_loc} to {to_loc} in {time_m} minutes.",
                severity="CRITICAL"
            ))

        # 7. High Severity Event Types
        high_sev_events = [e for e in events if e.get("event_type") in [
            "SUSPICIOUS_FILE_ACCESS", "PRIVILEGE_ESCALATION", "DATA_EXFILTRATION", "COMMAND_INJECTION"
        ]]
        if high_sev_events:
            pts = 25
            score += pts
            types = list(set(e.get("event_type") for e in high_sev_events))
            reasons.append(f"High-impact malicious event types detected: {', '.join(types)}.")
            breakdown.append(RiskFactorExplanation(
                factor_name="High-Impact Malicious Actions",
                points_contributed=pts,
                description=f"Critical actions executed: {', '.join(types)}.",
                severity="CRITICAL"
            ))

        # 8. Cryptographic Tamper Warning
        tampered_events = [e for e in events if e.get("integrity_status") == "TAMPERED"]
        if tampered_events:
            pts = 35
            score += pts
            reasons.append(f"🔐 Cryptographic Integrity Warning: {len(tampered_events)} log event(s) failed HMAC verification (tampering detected).")
            breakdown.append(RiskFactorExplanation(
                factor_name="Log Integrity Tampering",
                points_contributed=pts,
                description="HMAC signature discrepancy detected. Log payload altered in transit or at rest.",
                severity="CRITICAL"
            ))

        # Cap score at 100
        score = min(100, max(0, score))

        # Determine Risk Band
        if score <= self.threshold_low:
            risk_level = "LOW"
        elif score <= self.threshold_med:
            risk_level = "MEDIUM"
        elif score <= self.threshold_high:
            risk_level = "HIGH"
        else:
            risk_level = "VERY_HIGH"

        # Supervised ML Model Hybrid Enrichment
        latest_event = events[-1] if events else {}
        ml_ctx = dict(context)
        ml_ctx["cross_location_count"] = len(unique_locations)
        ml_ctx["success_after_failures"] = has_success_after_failure

        ml_res = ml_classifier.predict(latest_event, ml_ctx)

        # Generate Actionable SOC Recommendations
        recommendation = self._generate_recommendation(risk_level, breakdown, events)

        return RiskAssessment(
            overall_score=score,
            risk_level=risk_level,
            confidence=0.95 if breakdown else 1.0,
            reasons=reasons,
            factor_breakdown=breakdown,
            ml_prediction=ml_res.get("predicted_class"),
            ml_confidence=ml_res.get("confidence"),
            ml_feature_contributions=ml_res.get("feature_contributions", {}),
            recommended_action=recommendation
        )

    def _generate_recommendation(self, risk_level: str, breakdown: List[RiskFactorExplanation], events: List[Dict[str, Any]]) -> str:
        factor_names = [f.factor_name for f in breakdown]
        user_id = events[0].get("user_id", "the user") if events else "the account"

        if risk_level == "VERY_HIGH":
            return (
                f"🚨 IMMEDIATE CONTAINMENT REQUIRED:\n"
                f"1. Terminate all active sessions and revoke Kerberos tickets for {user_id}.\n"
                f"2. Temporarily isolate affected endpoints ({', '.join(set(e.get('server_id', '') for e in events))}) from organizational network.\n"
                f"3. Enforce perimeter firewall IP block on originating external/internal source IPs.\n"
                f"4. Initiate forensic snapshot of target databases and file servers.\n"
                f"5. Notify Sector Commander and Chief Information Security Officer (CISO)."
            )
        elif risk_level == "HIGH":
            return (
                f"⚠️ HIGH PRIORITY SOC ACTION:\n"
                f"1. Prompt user {user_id} for mandatory biometric/hardware token MFA re-verification.\n"
                f"2. Block unregistered devices ({', '.join(set(e.get('device_id', '') for e in events if e.get('unknown_device')))}) at NAC/VPN gateway.\n"
                f"3. Review audit logs on server {events[-1].get('server_id', 'target')} for unauthorized changes.\n"
                f"4. Monitor account for additional cross-location login attempts over the next 24 hours."
            )
        elif risk_level == "MEDIUM":
            return (
                f"📋 ELEVATED MONITORING:\n"
                f"1. Verify recent authentication attempts with user {user_id} via out-of-band channel (phone/radio).\n"
                f"2. Check if repeated password failures were due to expired credentials or cached client tokens.\n"
                f"3. Maintain heightened telemetry on the host workstation."
            )
        else:
            return "✅ ROUTINE MONITORING: Activity consistent with normal operational baseline. No immediate intervention required."


# Global singleton instance
risk_scorer = RiskScorer()
