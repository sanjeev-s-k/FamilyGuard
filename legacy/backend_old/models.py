"""
Data Models and Enums for IT System Log Analyzer
Centralized Cross-Location Threat Correlation & Explainable Risk Assessment
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Optional, Any
import uuid


class Location(str, Enum):
    NORTH = "North"
    SOUTH = "South"
    EAST = "East"
    WEST = "West"


class EventType(str, Enum):
    FAILED_LOGIN = "FAILED_LOGIN"
    SUCCESSFUL_LOGIN = "SUCCESSFUL_LOGIN"
    SUSPICIOUS_FILE_ACCESS = "SUSPICIOUS_FILE_ACCESS"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    PORT_SCAN = "PORT_SCAN"
    ACCOUNT_MODIFIED = "ACCOUNT_MODIFIED"
    COMMAND_INJECTION = "COMMAND_INJECTION"
    UNAUTHORIZED_CONFIG_CHANGE = "UNAUTHORIZED_CONFIG_CHANGE"
    MALWARE_BEACON = "MALWARE_BEACON"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class IntegrityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"
    UNVERIFIED = "UNVERIFIED"


class AgentStatusEnum(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    SYNCING = "SYNCING"


@dataclass
class LogEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    location: str = "North"
    server_id: str = "N-01"
    user_id: str = "user_u102"
    account: str = "u102_operator"
    device_id: str = "DEV-WIN-9021"
    source_ip: str = "10.14.2.19"
    event_type: str = "FAILED_LOGIN"
    login_status: str = "FAILURE"  # SUCCESS, FAILURE, N/A
    failed_attempt_count: int = 1
    unusual_location: bool = False
    unusual_time: bool = False
    unknown_device: bool = False
    account_verified: bool = True
    integrity_status: str = IntegrityStatus.VERIFIED.value
    hash_signature: str = ""
    raw_log: str = ""
    target_resource: str = "/var/log/auth"
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskFactorExplanation:
    factor_name: str
    points_contributed: int
    description: str
    severity: str = "INFO"  # INFO, WARNING, CRITICAL


@dataclass
class RiskAssessment:
    overall_score: int  # 0 to 100
    risk_level: str  # LOW, MEDIUM, HIGH, VERY_HIGH
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    factor_breakdown: List[RiskFactorExplanation]
    ml_prediction: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_feature_contributions: Dict[str, float] = field(default_factory=dict)
    recommended_action: str = ""
    calculated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["factor_breakdown"] = [asdict(f) if hasattr(f, "__dict__") else f for f in self.factor_breakdown]
        return data


@dataclass
class AttackGraphNode:
    id: str
    label: str
    type: str  # user, location, server, device, ip, action, resource
    risk_level: str = "LOW"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttackGraphEdge:
    source: str
    target: str
    label: str
    timestamp: str = ""
    severity: str = "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttackGraph:
    nodes: List[AttackGraphNode] = field(default_factory=list)
    edges: List[AttackGraphEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }


@dataclass
class TimelineStep:
    step_number: int
    timestamp: str
    location: str
    server_id: str
    user_id: str
    device_id: str
    source_ip: str
    event_type: str
    description: str
    risk_impact: str  # LOW, MEDIUM, HIGH, CRITICAL
    event_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CorrelatedIncident:
    incident_id: str = field(default_factory=lambda: f"INC-{uuid.uuid4().hex[:8].upper()}")
    title: str = ""
    user_id: str = ""
    primary_location: str = ""
    involved_locations: List[str] = field(default_factory=list)
    involved_servers: List[str] = field(default_factory=list)
    involved_devices: List[str] = field(default_factory=list)
    involved_ips: List[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    event_count: int = 0
    event_ids: List[str] = field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    timeline: List[TimelineStep] = field(default_factory=list)
    attack_graph: Optional[AttackGraph] = None
    scenario_tag: str = ""  # SCENARIO_A, SCENARIO_B, SCENARIO_C, SCENARIO_D, CUSTOM
    status: str = "OPEN"  # OPEN, INVESTIGATING, CONTAINED, RESOLVED, FALSE_POSITIVE
    assigned_analyst: str = "SOC Analyst 1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "user_id": self.user_id,
            "primary_location": self.primary_location,
            "involved_locations": self.involved_locations,
            "involved_servers": self.involved_servers,
            "involved_devices": self.involved_devices,
            "involved_ips": self.involved_ips,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "event_count": self.event_count,
            "event_ids": self.event_ids,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "timeline": [t.to_dict() for t in self.timeline],
            "attack_graph": self.attack_graph.to_dict() if self.attack_graph else None,
            "scenario_tag": self.scenario_tag,
            "status": self.status,
            "assigned_analyst": self.assigned_analyst
        }


@dataclass
class LocalAgent:
    location: str
    agent_id: str
    status: str = AgentStatusEnum.ONLINE.value
    ip_address: str = "10.0.0.1"
    server_ids: List[str] = field(default_factory=list)
    total_logs_collected: int = 0
    buffered_logs_count: int = 0
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    buffer: List[LogEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location,
            "agent_id": self.agent_id,
            "status": self.status,
            "ip_address": self.ip_address,
            "server_ids": self.server_ids,
            "total_logs_collected": self.total_logs_collected,
            "buffered_logs_count": len(self.buffer),
            "last_heartbeat": self.last_heartbeat
        }
