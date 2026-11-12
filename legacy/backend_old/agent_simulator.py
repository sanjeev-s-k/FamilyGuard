"""
Local Agent Simulation and Offline Synchronization Engine
Simulates edge log collectors running across North, South, East, and West locations.
Handles local log collection, normalization, offline queuing during network interruption,
and automatic resynchronization when connection is restored.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid

from backend.models import LocalAgent, AgentStatusEnum, LogEvent
from backend.normalizer import LogNormalizer
from backend.database import DatabaseManager


class AgentManager:
    """Manages simulated local agents across all geographical locations."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.agents: Dict[str, LocalAgent] = {
            "North": LocalAgent(
                location="North",
                agent_id="AGENT-NORTH-HQ",
                status=AgentStatusEnum.ONLINE.value,
                ip_address="10.14.0.1",
                server_ids=["N-01 (Domain Controller)", "N-02 (Central DB)", "N-03 (Web Portal)"]
            ),
            "South": LocalAgent(
                location="South",
                agent_id="AGENT-SOUTH-HUB",
                status=AgentStatusEnum.ONLINE.value,
                ip_address="10.22.0.1",
                server_ids=["S-01 (Regional Gateway)", "S-02 (Tactical Operations)"]
            ),
            "East": LocalAgent(
                location="East",
                agent_id="AGENT-EAST-SECTOR",
                status=AgentStatusEnum.ONLINE.value,
                ip_address="10.33.0.1",
                server_ids=["E-01 (Comms Server)", "E-02 (Classified Archives)"]
            ),
            "West": LocalAgent(
                location="West",
                agent_id="AGENT-WEST-COMMAND",
                status=AgentStatusEnum.ONLINE.value,
                ip_address="10.44.0.1",
                server_ids=["W-01 (Frontier Relay)", "W-02 (Logistics DB)"]
            )
        }
        self._init_db_agents()

    def _init_db_agents(self):
        for loc, agent in self.agents.items():
            self.db.update_agent_status(loc, agent.status, len(agent.buffer))

    def get_agent(self, location: str) -> Optional[LocalAgent]:
        return self.agents.get(location)

    def get_all_agents(self) -> List[Dict[str, Any]]:
        return [agent.to_dict() for agent in self.agents.values()]

    def set_agent_status(self, location: str, status: str) -> Dict[str, Any]:
        """Toggles agent connectivity (ONLINE / OFFLINE)."""
        if location not in self.agents:
            raise ValueError(f"Unknown location: {location}")

        agent = self.agents[location]
        agent.status = status
        agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
        self.db.update_agent_status(location, status, len(agent.buffer))

        return agent.to_dict()

    def collect_log(self, location: str, raw_event_or_text: Any, server_id: str = "N-01") -> Dict[str, Any]:
        """
        Local agent collects a log:
        1. Normalizes log and computes HMAC hash.
        2. If agent is ONLINE: immediately ingests to Central Analyzer.
        3. If agent is OFFLINE: buffers in local queue and increments buffer counter.
        """
        if location not in self.agents:
            raise ValueError(f"Unknown agent location: {location}")

        agent = self.agents[location]
        agent.total_logs_collected += 1
        agent.last_heartbeat = datetime.now(timezone.utc).isoformat()

        # Normalize
        if isinstance(raw_event_or_text, str):
            event = LogNormalizer.normalize_raw_log(raw_event_or_text, location=location, server_id=server_id)
        elif isinstance(raw_event_or_text, dict):
            event = LogNormalizer.normalize_dict(raw_event_or_text)
            event["location"] = location
        else:
            raise ValueError("Invalid log format")

        if agent.status == AgentStatusEnum.ONLINE.value:
            # Immediate transmission to Central Analyzer DB
            self.db.insert_event(event)
            status_msg = "Transmitted directly to Central Analyzer (Agent Online)"
            buffered = False
        else:
            # Buffer locally
            agent.buffer.append(event)
            self.db.update_agent_status(location, agent.status, len(agent.buffer))
            status_msg = f"Network disconnected. Log stored in local buffer (Queue depth: {len(agent.buffer)})"
            buffered = True

        return {
            "status": "SUCCESS",
            "buffered": buffered,
            "message": status_msg,
            "event": event,
            "agent": agent.to_dict()
        }

    def sync_agent_buffer(self, location: str) -> Dict[str, Any]:
        """
        Synchronizes buffered logs when connectivity is restored.
        Drains the agent buffer, inserts into Central Analyzer DB, and updates agent state.
        """
        if location not in self.agents:
            raise ValueError(f"Unknown agent location: {location}")

        agent = self.agents[location]
        buffered_events = list(agent.buffer)
        count = len(buffered_events)

        if count == 0:
            return {
                "status": "SUCCESS",
                "synced_count": 0,
                "message": f"Agent {location} has no buffered logs to synchronize.",
                "agent": agent.to_dict()
            }

        # Set status to syncing temporarily
        agent.status = AgentStatusEnum.ONLINE.value

        # Ingest buffered events to DB in batch
        self.db.insert_events_batch(buffered_events)

        # Clear buffer
        agent.buffer.clear()
        self.db.update_agent_status(location, agent.status, 0)

        return {
            "status": "SUCCESS",
            "synced_count": count,
            "message": f"Successfully synchronized {count} buffered logs from Agent {location} to Central Threat Intelligence.",
            "synced_events": buffered_events,
            "agent": agent.to_dict()
        }
