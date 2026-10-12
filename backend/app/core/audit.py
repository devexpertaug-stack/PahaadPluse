"""Audit logging scaffold.

Placeholder for FEAT-001. Later features persist audit entries so every
displayed number is traceable to source records (Req 27). For now this provides
a minimal in-memory recorder with a stable interface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger("pahadpulse.audit")


@dataclass
class AuditEntry:
    """A single audit record."""

    action: str
    actor: str
    detail: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditLog:
    """Minimal audit log recorder (in-memory placeholder)."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, action: str, actor: str, detail: str = "") -> AuditEntry:
        """Record and return an audit entry."""
        entry = AuditEntry(action=action, actor=actor, detail=detail)
        self._entries.append(entry)
        logger.info("audit action=%s actor=%s detail=%s", action, actor, detail)
        return entry

    @property
    def entries(self) -> list[AuditEntry]:
        """Return a copy of recorded entries."""
        return list(self._entries)


audit_log = AuditLog()
