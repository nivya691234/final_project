"""
core/action_history.py
----------------------
Unified action history and summary views.
Provides filtered, aggregated remediation activity across all mechanisms
(automatic policy, manual, AI agent).
"""

import logging
from typing import Dict, List, Optional
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ActionHistorySummary:
    """Query and summarize all remediation actions."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_summary(self, hours: int = 1) -> Dict:
        """
        Get aggregated summary of all actions in recent N hours.
        Returns counts by action type, status, severity.
        """
        cutoff_ts = self._now() - (hours * 3600)
        rows = self.db._query(
            """
            SELECT action, status, severity, source, COUNT(*) as count
            FROM action_queue
            WHERE timestamp >= ?
            GROUP BY action, status, severity, source
            """,
            (cutoff_ts,),
        )

        by_action = {}
        by_status = {}
        by_severity = {}
        by_source = {}

        for row in rows:
            action = dict(row)
            count = action.pop("count", 0)

            # By action
            if action["action"] not in by_action:
                by_action[action["action"]] = 0
            by_action[action["action"]] += count

            # By status
            if action["status"] not in by_status:
                by_status[action["status"]] = 0
            by_status[action["status"]] += count

            # By severity
            if action["severity"] not in by_severity:
                by_severity[action["severity"]] = 0
            by_severity[action["severity"]] += count

            # By source
            if action["source"] not in by_source:
                by_source[action["source"]] = 0
            by_source[action["source"]] += count

        return {
            "hours": hours,
            "by_action": by_action,
            "by_status": by_status,
            "by_severity": by_severity,
            "by_source": by_source,
            "total": sum(by_action.values()),
        }

    def get_recent_actions(
        self, limit: int = 50, status: Optional[str] = None, action: Optional[str] = None
    ) -> List[Dict]:
        """Get recent actions with optional filters."""
        query = "SELECT * FROM action_queue WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if action:
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self.db._query(query, tuple(params))
        return [dict(r) for r in rows]

    def get_failed_actions(self, limit: int = 20) -> List[Dict]:
        """Get actions that failed, to aid in debugging."""
        return self.get_recent_actions(limit=limit, status="FAILED")

    def get_success_rate(self, hours: int = 1) -> float:
        """Calculate success rate of actions in recent N hours (0-1)."""
        cutoff_ts = self._now() - (hours * 3600)
        total = self.db._query(
            "SELECT COUNT(*) as cnt FROM action_queue WHERE timestamp >= ?",
            (cutoff_ts,),
        )[0]["cnt"]

        if total == 0:
            return 0.0

        success = self.db._query(
            "SELECT COUNT(*) as cnt FROM action_queue WHERE timestamp >= ? AND status = 'EXECUTED'",
            (cutoff_ts,),
        )[0]["cnt"]

        return success / total

    def get_action_timeline(self, hours: int = 1, bucket_minutes: int = 5) -> List[Dict]:
        """
        Return timeline of action counts bucketed by time.
        Useful for dashboards showing action frequency.
        """
        cutoff_ts = self._now() - (hours * 3600)
        bucket_sec = bucket_minutes * 60

        rows = self.db._query(
            """
            SELECT 
                CAST((timestamp - ?) / ? AS INT) as bucket,
                COUNT(*) as count
            FROM action_queue
            WHERE timestamp >= ?
            GROUP BY bucket
            ORDER BY bucket
            """,
            (cutoff_ts, bucket_sec, cutoff_ts),
        )

        timeline = []
        for row in rows:
            bucket_idx = dict(row)["bucket"]
            ts = cutoff_ts + (bucket_idx * bucket_sec)
            timeline.append({"timestamp": ts, "count": dict(row)["count"]})

        return timeline

    def get_actions_by_target(self, limit: int = 20) -> List[Dict]:
        """Rank targets (processes) by number of actions taken against them."""
        rows = self.db._query(
            """
            SELECT target, COUNT(*) as action_count, 
                   GROUP_CONCAT(DISTINCT action) as actions
            FROM action_queue
            WHERE target IS NOT NULL
            GROUP BY target
            ORDER BY action_count DESC
            LIMIT ?
            """,
            (limit,),
        )

        return [
            {
                "target": dict(r)["target"],
                "action_count": dict(r)["action_count"],
                "actions": dict(r)["actions"].split(","),
            }
            for r in rows
        ]

    def get_action_impact_summary(self) -> Dict:
        """
        Estimate impact: correlate actions with improvement in system metrics.
        (Advanced: would require before/after metric snapshots.)
        """
        executed = self.db._query(
            """
            SELECT 
                action, 
                COUNT(*) as count,
                AVG(severity_rank) as avg_severity
            FROM (
                SELECT action, (
                    CASE severity 
                        WHEN 'CRITICAL' THEN 4
                        WHEN 'HIGH' THEN 3
                        WHEN 'MEDIUM' THEN 2
                        WHEN 'LOW' THEN 1
                        ELSE 0
                    END
                ) as severity_rank
                FROM action_queue
                WHERE status = 'EXECUTED'
            )
            GROUP BY action
            ORDER BY count DESC
            """
        )

        return {
            "most_used_action": dict(executed[0]) if executed else {},
            "actions_by_frequency": [dict(r) for r in executed],
        }

    @staticmethod
    def _now() -> float:
        import time
        return time.time()
