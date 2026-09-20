"""Versioned strategy registry and promotion gate.

Strategies are candidates until explicitly promoted after regression evidence.
The registry never edits application code; it stores strategy definitions and
their evidence so a later runtime can select only approved strategies.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from security_utils import validate_component, safe_child_path


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    name: str
    status: str
    source: str
    objective: str
    rules: tuple[str, ...] = ()
    required_tests: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: str = ""
    promoted_at: Optional[str] = None
    retired_at: Optional[str] = None
    degradation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionDecision:
    strategy_id: str
    approved: bool
    reason: str
    baseline_score: float
    candidate_score: float
    required_tests: tuple[str, ...]
    passed_tests: tuple[str, ...] = ()
    regressions: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_strategy_id(name: str, rules: Iterable[str]) -> str:
    seed = str(name).strip() + "|" + "|".join(sorted(map(str, rules)))
    return "strat-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def create_candidate(
    name: str,
    objective: str,
    rules: Iterable[str],
    *,
    required_tests: Iterable[str] = (),
    evidence_ids: Iterable[str] = (),
    metrics: Optional[Dict[str, float]] = None,
    source: str = "experience-analysis",
) -> StrategyDefinition:
    rules = tuple(dict.fromkeys(str(x) for x in rules if str(x).strip()))
    if not rules:
        raise ValueError("A strategy requires at least one rule.")
    now = datetime.now(timezone.utc).isoformat()
    return StrategyDefinition(
        strategy_id=make_strategy_id(name, rules),
        name=name.strip(),
        status="candidate",
        source=source,
        objective=objective.strip(),
        rules=rules,
        required_tests=tuple(dict.fromkeys(str(x) for x in required_tests)),
        evidence_ids=tuple(dict.fromkeys(str(x) for x in evidence_ids)),
        metrics={k: float(v) for k, v in (metrics or {}).items()},
        created_at=now,
    )


def evaluate_promotion(
    strategy: StrategyDefinition,
    *,
    baseline_score: float,
    candidate_score: float,
    passed_tests: Iterable[str],
    min_improvement: float = 0.02,
    regressions: Iterable[str] = (),
    max_regressions: int = 0,
) -> PromotionDecision:
    passed = tuple(dict.fromkeys(str(x) for x in passed_tests))
    required = tuple(strategy.required_tests)
    missing = [test for test in required if test not in passed]
    improvement = float(candidate_score) - float(baseline_score)
    regression_list = tuple(dict.fromkeys(str(x) for x in regressions))
    approved = (
        not missing
        and improvement >= float(min_improvement)
        and len(regression_list) <= int(max_regressions)
    )
    reason = (
        "cumple pruebas, mejora mínima y límite de regresiones"
        if approved
        else "no cumple el umbral de promoción o presenta regresiones"
    )
    return PromotionDecision(
        strategy_id=strategy.strategy_id,
        approved=approved,
        reason=reason,
        baseline_score=float(baseline_score),
        candidate_score=float(candidate_score),
        required_tests=required,
        passed_tests=passed,
        regressions=regression_list,
    )


class StrategyRegistry:
    def __init__(self, chats_dir: str):
        self.chats_dir = chats_dir

    def _path(self, chat_id: str) -> str:
        chat_id = validate_component(chat_id, "chat_id")
        return safe_child_path(safe_child_path(self.chats_dir, chat_id), "estrategias.json")

    def _load(self, chat_id: str) -> Dict[str, Any]:
        path = self._path(chat_id)
        if not os.path.exists(path):
            return {"schema_version": 1, "strategies": []}
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, chat_id: str, data: Dict[str, Any]) -> None:
        path = self._path(chat_id)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def register(self, chat_id: str, strategy: StrategyDefinition) -> StrategyDefinition:
        data = self._load(chat_id)
        existing = [x for x in data["strategies"] if x.get("strategy_id") == strategy.strategy_id]
        if not existing:
            data["strategies"].append(strategy.to_dict())
            self._save(chat_id, data)
        return strategy

    def list(self, chat_id: str, status: Optional[str] = None) -> list[Dict[str, Any]]:
        items = self._load(chat_id)["strategies"]
        if status:
            items = [x for x in items if x.get("status") == status]
        return items

    def promote(self, chat_id: str, decision: PromotionDecision) -> Dict[str, Any]:
        if not decision.approved:
            raise ValueError("Una decisión no aprobada no puede promocionarse.")
        data = self._load(chat_id)
        for strategy in data["strategies"]:
            if strategy.get("strategy_id") == decision.strategy_id:
                strategy["status"] = "promoted"
                strategy["promoted_at"] = datetime.now(timezone.utc).isoformat()
                strategy["promotion"] = decision.to_dict()
                self._save(chat_id, data)
                return strategy
        raise KeyError(f"Strategy not found: {decision.strategy_id}")

    def retire(self, chat_id: str, strategy_id: str, *, reason: str, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = self._load(chat_id)
        for strategy in data["strategies"]:
            if strategy.get("strategy_id") == strategy_id:
                if strategy.get("status") != "promoted":
                    raise ValueError("Solo una estrategia promovida puede degradarse/retirarse.")
                strategy["status"] = "retired"
                strategy["retired_at"] = datetime.now(timezone.utc).isoformat()
                strategy["degradation"] = {
                    "reason": str(reason),
                    "evidence": evidence or {},
                }
                self._save(chat_id, data)
                return strategy
        raise KeyError(f"Strategy not found: {strategy_id}")

    def reactivate(self, chat_id: str, strategy_id: str, *, reason: str, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = self._load(chat_id)
        for strategy in data["strategies"]:
            if strategy.get("strategy_id") == strategy_id:
                if strategy.get("status") not in {"retired", "degraded"}:
                    raise ValueError("Solo una estrategia retirada o degradada puede reactivarse.")
                strategy["status"] = "promoted"
                strategy["reactivated_at"] = datetime.now(timezone.utc).isoformat()
                strategy["reactivation"] = {
                    "reason": str(reason),
                    "evidence": evidence or {},
                }
                self._save(chat_id, data)
                return strategy
        raise KeyError(f"Strategy not found: {strategy_id}")
