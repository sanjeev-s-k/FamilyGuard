"""
Identity Linking Engine
Tracks and aggregates user identity profiles, known devices, baseline locations,
and detects anomalous hops (such as impossible travel).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math

# Baseline user profiles for the organization (e.g. CRPF headquarters & regional wings)
USER_BASELINES: Dict[str, Dict[str, Any]] = {
    "user_u102": {
        "full_name": "Major Vikram Rathore (Signals / IT Lead)",
        "role": "Senior IT Administrator",
        "home_location": "North",
        "authorized_locations": ["North"],
        "known_devices": ["DEV-WIN-9021", "DEV-MAC-4102"],
        "known_ips": ["10.14.2.19", "10.14.2.20"],
        "standard_work_hours": (8, 20),
        "account_verified": True
    },
    "user_u204": {
        "full_name": "Inspector Priya Sharma",
        "role": "Logistics & Personnel Officer",
        "home_location": "South",
        "authorized_locations": ["South"],
        "known_devices": ["DEV-LAP-5512"],
        "known_ips": ["10.22.4.11"],
        "standard_work_hours": (9, 19),
        "account_verified": True
    },
    "user_u308": {
        "full_name": "Sub-Inspector Amit Verma",
        "role": "East Sector Communications",
        "home_location": "East",
        "authorized_locations": ["East"],
        "known_devices": ["DEV-EAST-7721"],
        "known_ips": ["10.33.1.5"],
        "standard_work_hours": (7, 21),
        "account_verified": True
    },
    "admin_super": {
        "full_name": "Central System Root / HQ Admin",
        "role": "Superuser",
        "home_location": "North",
        "authorized_locations": ["North", "South", "East", "West"],
        "known_devices": ["DEV-HQ-SEC01"],
        "known_ips": ["10.14.1.1"],
        "standard_work_hours": (0, 24),
        "account_verified": True
    }
}

# Approximate geographic distances (km) between regional organizational hubs
LOCATION_DISTANCES = {
    ("North", "South"): 1800,
    ("North", "East"): 1500,
    ("North", "West"): 1100,
    ("South", "East"): 1600,
    ("South", "West"): 1000,
    ("East", "West"): 2200,
}


def get_location_distance(loc1: str, loc2: str) -> int:
    if loc1 == loc2:
        return 0
    pair = (loc1, loc2)
    rev_pair = (loc2, loc1)
    return LOCATION_DISTANCES.get(pair, LOCATION_DISTANCES.get(rev_pair, 1200))


class IdentityLinker:
    """Links disparate log events into unified user/device identity context."""

    def __init__(self):
        self.profiles = dict(USER_BASELINES)

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        if user_id in self.profiles:
            return self.profiles[user_id]
        return {
            "full_name": f"User {user_id.upper()}",
            "role": "Standard User",
            "home_location": "North",
            "authorized_locations": ["North"],
            "known_devices": ["DEV-WIN-9021"],
            "known_ips": ["10.14.2.19"],
            "standard_work_hours": (8, 20),
            "account_verified": True
        }

    def assess_identity_context(self, event: Dict[str, Any], previous_events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Enriches an event with identity-linking context:
        - Checks if location is unusual for this user
        - Checks if device is unknown
        - Checks for impossible travel speed vs previous event
        """
        user_id = event.get("user_id", "user_unknown")
        profile = self.get_profile(user_id)
        location = event.get("location", "North")
        device_id = event.get("device_id", "DEV-UNKNOWN")

        # 1. Unusual Location Check
        is_unusual_location = location not in profile.get("authorized_locations", [profile.get("home_location", "North")])
        if "unusual_location" in event:
            is_unusual_location = is_unusual_location or bool(event["unusual_location"])

        # 2. Unknown Device Check
        is_unknown_device = device_id not in profile.get("known_devices", [])
        if "unknown_device" in event:
            is_unknown_device = is_unknown_device or bool(event["unknown_device"])

        # 3. Impossible Travel Check (Velocity between consecutive logins across locations)
        impossible_travel = False
        travel_details = None

        if previous_events:
            for prev in reversed(previous_events):
                if prev.get("user_id") == user_id and prev.get("location") != location:
                    try:
                        t1 = datetime.fromisoformat(prev.get("timestamp", "").replace("Z", "+00:00"))
                        t2 = datetime.fromisoformat(event.get("timestamp", "").replace("Z", "+00:00"))
                        time_delta_hours = abs((t2 - t1).total_seconds()) / 3600.0

                        distance_km = get_location_distance(prev.get("location", ""), location)
                        if distance_km > 0:
                            # If elapsed time < 2 hours for >1000km distance, impossible physical travel!
                            required_speed_kmh = distance_km / max(time_delta_hours, 0.01)
                            if required_speed_kmh > 800:  # Faster than commercial airline
                                impossible_travel = True
                                travel_details = {
                                    "from_location": prev.get("location"),
                                    "to_location": location,
                                    "distance_km": distance_km,
                                    "time_diff_minutes": round(time_delta_hours * 60, 1),
                                    "calculated_speed_kmh": round(required_speed_kmh, 1)
                                }
                                break
                    except Exception:
                        pass

        return {
            "profile": profile,
            "is_unusual_location": is_unusual_location,
            "is_unknown_device": is_unknown_device,
            "impossible_travel": impossible_travel,
            "travel_details": travel_details
        }
