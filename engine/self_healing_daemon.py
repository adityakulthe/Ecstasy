"""
Autonomous Continuous Repository Self-Healing Daemon ("Ecstasy Watch")
Part of Ecstasy Provable Cyber Defense (PCD)

Continuously watches source and LLVM IR repositories for file modifications, immediately runs
the Z3 SMT vulnerability prover on dirty buffers, synthesizes Zero-Divergence branchless
security patches, updates working trees or generates git diff commits, and exports signed
in-toto v1.0 supply-chain attestations in real time.
"""

from __future__ import annotations

import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from engine.self_healing_guard import SelfHealingGuard, SelfHealingResult


@dataclass
class WatchEvent:
    """Record of a file modification and automated healing event."""
    timestamp: str
    file_path: str
    status: str  # "CLEAN", "HEALED", "ERROR"
    vulnerabilities_healed: int
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DaemonStatus:
    """Live status report of the Ecstasy self-healing watch daemon."""
    repo_dir: str
    is_running: bool
    files_tracked: int
    events_processed: int
    vulnerabilities_healed_total: int
    recent_events: List[WatchEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_dir": self.repo_dir,
            "is_running": self.is_running,
            "files_tracked": self.files_tracked,
            "events_processed": self.events_processed,
            "vulnerabilities_healed_total": self.vulnerabilities_healed_total,
            "recent_events": [e.to_dict() for e in self.recent_events],
        }


class SelfHealingDaemon:
    """
    Continuous background file-watcher and autonomous vulnerability repair daemon.
    """

    def __init__(
        self,
        repo_dir: Optional[str] = None,
        poll_interval: float = 1.0,
        auto_patch: bool = False,
        timeout_sec: int = 15,
    ):
        self.repo_dir = repo_dir or "."
        self.poll_interval = poll_interval
        self.auto_patch = auto_patch
        self.guard = SelfHealingGuard(timeout_sec=timeout_sec)
        self.file_hashes: Dict[str, str] = {}
        self.events: List[WatchEvent] = []
        self.vulnerabilities_healed_total: int = 0
        self.is_running: bool = False

    def _compute_hash(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def scan_and_heal_once(
        self,
        repo_dir: str,
        auto_patch: bool = False,
        output_dir: Optional[str] = None,
        callback: Optional[Callable[[WatchEvent], None]] = None,
    ) -> List[SelfHealingResult]:
        """
        Scan all files in repo_dir; heal only modified or un-cached files.
        """
        base_p = Path(repo_dir)
        if not base_p.exists():
            return []

        results: List[SelfHealingResult] = []

        for p in base_p.rglob("*"):
            if not p.is_file():
                continue
            if any(part.startswith(".") for part in p.parts):
                continue
            if "node_modules" in p.parts or "__pycache__" in p.parts or "test" in p.parts:
                continue

            if p.suffix in (".c", ".ll"):
                str_p = str(p)
                curr_hash = self._compute_hash(p)
                if not curr_hash:
                    continue

                # Check if file has changed
                if str_p not in self.file_hashes or self.file_hashes[str_p] != curr_hash:
                    self.file_hashes[str_p] = curr_hash
                    res = self.guard.audit_and_heal_file(str_p, auto_patch=auto_patch, output_dir=output_dir)
                    results.append(res)

                    now_str = datetime.now(timezone.utc).isoformat()
                    evt = WatchEvent(
                        timestamp=now_str,
                        file_path=str_p,
                        status=res.status,
                        vulnerabilities_healed=res.patches_applied_count,
                        details=f"Audited {p.name}: {res.status} ({res.patches_applied_count} patch(es) applied)",
                    )
                    self.events.append(evt)
                    self.vulnerabilities_healed_total += res.patches_applied_count

                    if callback:
                        callback(evt)

        return results

    def watch_repository(
        self,
        repo_dir: str,
        poll_interval_sec: float = 1.0,
        max_cycles: Optional[int] = None,
        auto_patch: bool = False,
        output_dir: Optional[str] = None,
        callback: Optional[Callable[[WatchEvent], None]] = None,
    ) -> DaemonStatus:
        """
        Run the continuous watch loop for a specified number of cycles or indefinitely.
        """
        self.is_running = True
        cycle = 0

        try:
            while self.is_running:
                self.scan_and_heal_once(
                    repo_dir,
                    auto_patch=auto_patch,
                    output_dir=output_dir,
                    callback=callback,
                )
                cycle += 1
                if max_cycles is not None and cycle >= max_cycles:
                    break
                time.sleep(poll_interval_sec)
        finally:
            self.is_running = False

        return self.get_status(repo_dir)

    def get_status(self, repo_dir: Optional[str] = None) -> DaemonStatus:
        """Return current status of the daemon."""
        return DaemonStatus(
            repo_dir=repo_dir or self.repo_dir,
            is_running=self.is_running,
            files_tracked=len(self.file_hashes),
            events_processed=len(self.events),
            vulnerabilities_healed_total=self.vulnerabilities_healed_total,
            recent_events=self.events[-10:],
        )

    def run_single_scan(
        self,
        repo_dir: Optional[str] = None,
        auto_patch: Optional[bool] = None,
        output_dir: Optional[str] = None,
    ) -> DaemonStatus:
        """Run a single audit scan across all target files in the repository."""
        target_dir = repo_dir or self.repo_dir
        patch_flag = self.auto_patch if auto_patch is None else auto_patch
        self.scan_and_heal_once(target_dir, auto_patch=patch_flag, output_dir=output_dir)
        return self.get_status(target_dir)

    def start_daemon(
        self,
        max_iterations: Optional[int] = None,
        repo_dir: Optional[str] = None,
        auto_patch: Optional[bool] = None,
    ) -> DaemonStatus:
        """Start the continuous watcher loop."""
        target_dir = repo_dir or self.repo_dir
        patch_flag = self.auto_patch if auto_patch is None else auto_patch
        return self.watch_repository(
            repo_dir=target_dir,
            poll_interval_sec=self.poll_interval,
            max_cycles=max_iterations,
            auto_patch=patch_flag,
        )
