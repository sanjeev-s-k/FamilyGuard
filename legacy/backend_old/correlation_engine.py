"""
Cross-Location Threat Correlation Engine (CORE INNOVATION)
Correlates security events across distributed geographical locations, servers, users,
devices, and time windows. Generates attack graphs, chronological timelines, and unified incident packages.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from backend.models import (
    CorrelatedIncident, TimelineStep, AttackGraph, AttackGraphNode, AttackGraphEdge
)
from backend.identity_linker import IdentityLinker
from backend.risk_scorer import risk_scorer


class CrossLocationCorrelationEngine:
    """Core Threat Correlation Engine."""

    def __init__(self):
        self.identity_linker = IdentityLinker()

    def correlate_user_events(
        self,
        events: List[Dict[str, Any]],
        scenario_tag: str = "CUSTOM",
        incident_id: Optional[str] = None
    ) -> CorrelatedIncident:
        """
        Takes a cluster of related events (typically grouped by user, session, or entity)
        and runs cross-location threat correlation.
        """
        if not events:
            raise ValueError("Cannot correlate empty event list")

        # Sort events chronologically
        events = sorted(events, key=lambda x: x.get("timestamp", ""))

        primary_user = events[0].get("user_id", "unknown_user")
        primary_location = events[0].get("location", "North")

        involved_locations = list(dict.fromkeys([e.get("location") for e in events if e.get("location")]))
        involved_servers = list(dict.fromkeys([e.get("server_id") for e in events if e.get("server_id")]))
        involved_devices = list(dict.fromkeys([e.get("device_id") for e in events if e.get("device_id")]))
        involved_ips = list(dict.fromkeys([e.get("source_ip") for e in events if e.get("source_ip")]))
        event_ids = [e.get("event_id") for e in events if e.get("event_id")]

        start_time = events[0].get("timestamp", "")
        end_time = events[-1].get("timestamp", "")

        # 1. Identity & Context assessment across the chain
        context = {
            "cross_location_count": len(involved_locations),
            "is_unusual_location": False,
            "is_unknown_device": False,
            "impossible_travel": False,
            "travel_details": None
        }

        for idx, ev in enumerate(events):
            prev_events = events[:idx]
            id_eval = self.identity_linker.assess_identity_context(ev, prev_events)
            if id_eval.get("is_unusual_location"):
                context["is_unusual_location"] = True
            if id_eval.get("is_unknown_device"):
                context["is_unknown_device"] = True
            if id_eval.get("impossible_travel"):
                context["impossible_travel"] = True
                context["travel_details"] = id_eval.get("travel_details")

        # 2. Risk Score & Explanation
        risk_assessment = risk_scorer.calculate_risk(events, context)

        # 3. Generate Attack Timeline
        timeline = self._generate_timeline(events)

        # 4. Generate Attack Graph
        attack_graph = self._generate_attack_graph(events, primary_user, risk_assessment.risk_level)

        # Generate a descriptive incident title
        title = self._generate_incident_title(primary_user, involved_locations, risk_assessment.risk_level, events)

        inc_id = incident_id or f"INC-{uuid.uuid4().hex[:8].upper()}"

        return CorrelatedIncident(
            incident_id=inc_id,
            title=title,
            user_id=primary_user,
            primary_location=primary_location,
            involved_locations=involved_locations,
            involved_servers=involved_servers,
            involved_devices=involved_devices,
            involved_ips=involved_ips,
            start_time=start_time,
            end_time=end_time,
            event_count=len(events),
            event_ids=event_ids,
            risk_assessment=risk_assessment,
            timeline=timeline,
            attack_graph=attack_graph,
            scenario_tag=scenario_tag,
            status="OPEN"
        )

    def _generate_timeline(self, events: List[Dict[str, Any]]) -> List[TimelineStep]:
        timeline_steps = []
        for idx, e in enumerate(events, 1):
            etype = e.get("event_type", "EVENT")
            loc = e.get("location", "Unknown")
            srv = e.get("server_id", "Unknown")
            dev = e.get("device_id", "Unknown")
            user = e.get("user_id", "Unknown")
            ip = e.get("source_ip", "0.0.0.0")

            # Craft human-readable step description
            if etype == "FAILED_LOGIN":
                cnt = e.get("failed_attempt_count", 1)
                desc = f"Failed authentication attempt (count: {cnt}) on {srv} from device {dev} ({ip})."
                impact = "MEDIUM" if cnt >= 5 else "LOW"
            elif etype == "SUCCESSFUL_LOGIN":
                if e.get("unusual_location") or e.get("unknown_device"):
                    desc = f"Successful logon to {srv} ({loc}) from UNRECOGNIZED hardware {dev} at unusual location."
                    impact = "HIGH"
                else:
                    desc = f"Successful user logon to {srv} from trusted device {dev}."
                    impact = "LOW"
            elif etype == "SUSPICIOUS_FILE_ACCESS":
                desc = f"Unauthorized access to sensitive repository {e.get('target_resource', '/data')} on {srv} ({loc})."
                impact = "HIGH"
            elif etype == "PRIVILEGE_ESCALATION":
                desc = f"Elevated root/admin privileges obtained on {srv} ({loc})."
                impact = "CRITICAL"
            elif etype == "DATA_EXFILTRATION":
                desc = f"Outbound bulk data exfiltration detected from {srv} to remote IP {ip}."
                impact = "CRITICAL"
            else:
                desc = f"{etype} recorded on {srv} in {loc}."
                impact = "MEDIUM"

            if e.get("integrity_status") == "TAMPERED":
                desc += " [⚠️ HMAC TAMPER WARNING]"
                impact = "CRITICAL"

            timeline_steps.append(TimelineStep(
                step_number=idx,
                timestamp=e.get("timestamp", ""),
                location=loc,
                server_id=srv,
                user_id=user,
                device_id=dev,
                source_ip=ip,
                event_type=etype,
                description=desc,
                risk_impact=impact,
                event_id=e.get("event_id", "")
            ))
        return timeline_steps

    def _generate_attack_graph(self, events: List[Dict[str, Any]], primary_user: str, risk_level: str) -> AttackGraph:
        """
        Builds a directed entity graph connecting:
        User Identity -> Devices -> Source IPs -> Locations -> Servers -> Malicious Actions / Targets
        """
        nodes_dict: Dict[str, AttackGraphNode] = {}
        edges_list: List[AttackGraphEdge] = []

        # 1. User Root Node
        user_node_id = f"user_{primary_user}"
        nodes_dict[user_node_id] = AttackGraphNode(
            id=user_node_id,
            label=f"Identity: {primary_user}",
            type="user",
            risk_level=risk_level,
            metadata={"user_id": primary_user}
        )

        for ev in events:
            loc = ev.get("location", "North")
            srv = ev.get("server_id", "N-01")
            dev = ev.get("device_id", "DEV-01")
            ip = ev.get("source_ip", "10.0.0.1")
            etype = ev.get("event_type", "INFO")
            target = ev.get("target_resource", "")

            # Location Node
            loc_id = f"loc_{loc}"
            if loc_id not in nodes_dict:
                nodes_dict[loc_id] = AttackGraphNode(
                    id=loc_id,
                    label=f"Location: {loc}",
                    type="location",
                    risk_level="HIGH" if ev.get("unusual_location") else "LOW",
                    metadata={"region": loc}
                )

            # Server Node
            srv_id = f"srv_{srv}"
            if srv_id not in nodes_dict:
                nodes_dict[srv_id] = AttackGraphNode(
                    id=srv_id,
                    label=f"Server: {srv} ({loc})",
                    type="server",
                    risk_level="HIGH" if etype in ["PRIVILEGE_ESCALATION", "DATA_EXFILTRATION"] else "LOW",
                    metadata={"server_id": srv, "location": loc}
                )
                # Link Location -> Server
                edges_list.append(AttackGraphEdge(
                    source=loc_id,
                    target=srv_id,
                    label="hosts",
                    severity="LOW"
                ))

            # Device Node
            dev_id = f"dev_{dev}"
            if dev_id not in nodes_dict:
                nodes_dict[dev_id] = AttackGraphNode(
                    id=dev_id,
                    label=f"Device: {dev}",
                    type="device",
                    risk_level="HIGH" if ev.get("unknown_device") else "LOW",
                    metadata={"device_id": dev}
                )
                # Link User -> Device
                edges_list.append(AttackGraphEdge(
                    source=user_node_id,
                    target=dev_id,
                    label="operates",
                    severity="HIGH" if ev.get("unknown_device") else "LOW"
                ))

            # IP Node
            ip_node_id = f"ip_{ip}"
            if ip_node_id not in nodes_dict:
                nodes_dict[ip_node_id] = AttackGraphNode(
                    id=ip_node_id,
                    label=f"IP: {ip}",
                    type="ip",
                    risk_level="HIGH" if ev.get("unknown_device") else "LOW",
                    metadata={"ip": ip}
                )
                # Link Device -> IP
                edges_list.append(AttackGraphEdge(
                    source=dev_id,
                    target=ip_node_id,
                    label="originates_from",
                    severity="LOW"
                ))

            # Link IP -> Server with event action
            edges_list.append(AttackGraphEdge(
                source=ip_node_id,
                target=srv_id,
                label=etype.lower(),
                timestamp=ev.get("timestamp", ""),
                severity="CRITICAL" if etype in ["DATA_EXFILTRATION", "PRIVILEGE_ESCALATION"] else "LOW"
            ))

            # Target Resource Node if high severity
            if target and target != "/system":
                tgt_id = f"tgt_{srv}_{abs(hash(target)) % 10000}"
                if tgt_id not in nodes_dict:
                    nodes_dict[tgt_id] = AttackGraphNode(
                        id=tgt_id,
                        label=f"Resource: {target}",
                        type="resource",
                        risk_level="CRITICAL",
                        metadata={"path": target}
                    )
                    edges_list.append(AttackGraphEdge(
                        source=srv_id,
                        target=tgt_id,
                        label="impacts",
                        severity="CRITICAL"
                    ))

        return AttackGraph(
            nodes=list(nodes_dict.values()),
            edges=edges_list
        )

    def _generate_incident_title(
        self,
        user_id: str,
        locations: List[str],
        risk_level: str,
        events: List[Dict[str, Any]]
    ) -> str:
        loc_str = " -> ".join(locations)
        if len(locations) >= 3:
            return f"🚨 Distributed Multi-Region Attack Chain across {loc_str} (User: {user_id})"
        elif len(locations) == 2:
            return f"⚠️ Cross-Location Lateral Hopping: {loc_str} (User: {user_id})"
        elif any(e.get("integrity_status") == "TAMPERED" for e in events):
            return f"🔐 Log Integrity Breach & Tampering Detected at {locations[0]} ({user_id})"
        elif risk_level in ["HIGH", "VERY_HIGH"]:
            return f"🔴 Anomalous High-Risk Authentication & Access at {locations[0]} ({user_id})"
        elif risk_level == "MEDIUM":
            return f"🟡 Repeated Authentication Failures at {locations[0]} ({user_id})"
        else:
            return f"🟢 Routine Authenticated Activity at {locations[0]} ({user_id})"


# Global singleton instance
correlation_engine = CrossLocationCorrelationEngine()
