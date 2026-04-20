"""
core/action_policy.py
---------------------
Rule-based auto-remediation policy engine.
Generates action proposals from recent root causes, predictions, and recommendations.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from config.settings import (
    AUTO_ALLOWED_ACTIONS,
    AUTO_DEDUP_WINDOW_SEC,
    AUTO_MAX_PROPOSALS,
    AUTO_POLICY_ENABLED,
    AUTO_POLICY_MODE,
    AUTO_PROB_THRESHOLD,
    AUTO_SEVERITY_MIN,
    IGNORE_PROCESS_NAMES,
)
from database.db_manager import DatabaseManager
from core.remediation import RemediationEngine
from core.pid_registry import get_registered_pids, get_registered_process_names

logger = logging.getLogger(__name__)

SEV_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

CAUSE_ACTION_PREFS = {
    "Memory Leak": ["restart", "kill", "lower_priority"],
    "CPU Runaway": ["limit_cpu", "lower_priority", "restart", "kill"],
    "Thread Leak": ["restart", "kill"],
    "Resource Exhaustion": ["restart", "kill"],
}

REC_ACTION_MAP = [
    ("restart", "restart"),
    ("kill", "kill"),
    ("lower priority", "lower_priority"),
    ("limit", "limit_cpu"),
]


class ActionPolicyEngine:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.remediator = RemediationEngine()

    def run(self) -> List[Dict]:
        if not AUTO_POLICY_ENABLED:
            return []

        proposals: List[Dict] = []

        proposals.extend(self._from_root_cause())
        proposals.extend(self._from_failure_probability())
        proposals.extend(self._from_recommendations())

        # Deduplicate and cap proposals
        unique = []
        for p in proposals:
            if self._is_duplicate(p):
                continue
            unique.append(p)
            if len(unique) >= AUTO_MAX_PROPOSALS:
                break

        saved = []
        for p in unique:
            saved.append(self._enqueue_or_execute(p))

        return saved

    def _from_root_cause(self) -> List[Dict]:
        rc = self.db.get_latest_root_cause() or {}
        if not rc:
            return []

        sev = rc.get("severity", "LOW")
        if SEV_ORDER.get(sev, 0) < SEV_ORDER.get(AUTO_SEVERITY_MIN, 0):
            return []

        cause = rc.get("cause")
        target = rc.get("name")
        if not cause or not target or target == "system":
            return []
        if target.lower() in {n.lower() for n in IGNORE_PROCESS_NAMES}:
            return []

        prefs = CAUSE_ACTION_PREFS.get(cause, [])
        action = self._pick_allowed_action(prefs)
        if not action:
            return []

        pid = self._latest_pid_for(target)
        if self._is_internal_target(target, pid):
            return []
        if action == "restart" and not pid:
            return []

        reason = f"Root cause {cause} ({sev})."
        return [self._proposal(action, target, pid, reason, source="root_cause", severity=sev)]

    def _from_failure_probability(self) -> List[Dict]:
        pred = self.db.get_latest_prediction() or {}
        p = pred.get("failure_probability", 0)
        if p < AUTO_PROB_THRESHOLD:
            return []

        rc = self.db.get_latest_root_cause() or {}
        target = rc.get("name")
        if not target or target == "system":
            return []
        if target.lower() in {n.lower() for n in IGNORE_PROCESS_NAMES}:
            return []

        action = self._pick_allowed_action(["restart", "kill", "lower_priority"])
        if not action:
            return []

        pid = self._latest_pid_for(target)
        if self._is_internal_target(target, pid):
            return []
        if action == "restart" and not pid:
            return []

        severity = "CRITICAL" if p >= AUTO_PROB_THRESHOLD else "HIGH"
        reason = f"Failure probability {p:.2f} exceeded threshold."
        return [self._proposal(action, target, pid, reason, source="prediction", severity=severity)]

    def _from_recommendations(self) -> List[Dict]:
        recs = self.db.get_recommendations(limit=5)
        proposals: List[Dict] = []

        for rec in recs:
            text = (rec.get("recommendation") or "").lower()
            target = self._extract_quoted_name(rec.get("recommendation") or "")
            if not target:
                continue
            if target.lower() == "system" or target.lower() in {n.lower() for n in IGNORE_PROCESS_NAMES}:
                continue

            action = None
            for key, mapped in REC_ACTION_MAP:
                if key in text:
                    action = self._pick_allowed_action([mapped])
                    break

            if not action:
                continue

            pid = self._latest_pid_for(target)
            if pid is not None and pid <= 4:
                continue
            if self._is_internal_target(target, pid):
                continue
            if action == "restart" and not pid:
                continue

            severity = rec.get("priority", "LOW")
            reason = "Recommendation triggered action."
            proposals.append(self._proposal(action, target, pid, reason, source="recommendation", severity=severity))

        return proposals

    def _proposal(
        self,
        action: str,
        target: str,
        pid: Optional[int],
        reason: str,
        source: str,
        severity: str = "LOW",
        params: Optional[Dict] = None,
    ) -> Dict:
        return {
            "timestamp": time.time(),
            "action": action,
            "target": target,
            "pid": pid,
            "params": params or {},
            "reason": reason,
            "source": source,
            "severity": severity,
            "status": "PENDING",
        }

    def _pick_allowed_action(self, preferred: List[str]) -> Optional[str]:
        for act in preferred:
            if act in AUTO_ALLOWED_ACTIONS:
                return act
        return None

    def _latest_pid_for(self, name: str) -> Optional[int]:
        row = self.db.get_latest_process_by_name(name)
        if not row:
            return None
        return row.get("pid")

    def _is_internal_target(self, target: str, pid: Optional[int]) -> bool:
        if not target:
            return False
        reg_pids = set(get_registered_pids())
        if pid and pid in reg_pids:
            return True
        if pid is not None and pid <= 4:
            return True
        reg_names = {n.lower() for n in get_registered_process_names()}
        return target.lower() in reg_names

    def _extract_quoted_name(self, text: str) -> Optional[str]:
        # Recommendation templates wrap names in single quotes.
        if "'" not in text:
            return None
        parts = text.split("'")
        return parts[1] if len(parts) >= 3 else None

    def _is_duplicate(self, proposal: Dict) -> bool:
        return self.db.action_exists_recent(
            action=proposal["action"],
            target=proposal.get("target"),
            pid=proposal.get("pid"),
            within_sec=AUTO_DEDUP_WINDOW_SEC,
        )

    def _enqueue_or_execute(self, proposal: Dict) -> Dict:
        if AUTO_POLICY_MODE == "auto":
            result = self.remediator.execute_action(
                proposal["action"],
                target=proposal.get("target"),
                pid=proposal.get("pid"),
                **proposal.get("params", {}),
            )
            status = "EXECUTED" if result.get("success") else "FAILED"
            proposal["status"] = status
            proposal["message"] = result.get("message", "")

        action_id = self.db.insert_action_item(proposal)
        proposal["id"] = action_id
        return proposal
