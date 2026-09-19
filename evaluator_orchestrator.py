"""Praxis evaluation orchestrator: evidence-aware, retryable, auditable."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
import hashlib
import json


@dataclass(frozen=True)
class Evidence:
    source: str
    kind: str
    content: Any
    confidence: float = 0.0


@dataclass(frozen=True)
class AgentResult:
    agent: str
    output: Any
    evidence: tuple[Evidence, ...] = ()
    status: str = "COMPLETED"


@dataclass(frozen=True)
class Evaluation:
    consistent: bool
    score: float
    errors: tuple[str, ...] = ()
    strengths: tuple[str, ...] = ()
    required_retries: tuple[str, ...] = ()
    recommendation: str = "ACCEPT"
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImprovementProposal:
    target: str
    reason: str
    strategy: str
    expected_effect: str
    tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearningRecord:
    record_id: str
    created_at: str
    task_fingerprint: str
    agent_results: tuple[AgentResult, ...]
    evaluation: Evaluation
    proposal: ImprovementProposal | None
    strategy_id: str


class EvaluationOrchestrator:
    """Run answer -> review -> evidence/CAS -> evaluation -> retry -> learning record."""

    def __init__(self, answer_agent: Callable, review_agent: Callable,
                 cas_verifier: Callable | None = None,
                 rag_provider: Callable | None = None,
                 max_retries: int = 2):
        self.answer_agent = answer_agent
        self.review_agent = review_agent
        self.cas_verifier = cas_verifier
        self.rag_provider = rag_provider
        self.max_retries = max_retries

    @staticmethod
    def fingerprint(task: str) -> str:
        return hashlib.sha256(task.strip().encode("utf-8")).hexdigest()[:16]

    def _evaluate(self, answer, review, cas, rag):
        errors = []
        reasons = []
        strengths = []
        if review and isinstance(review.output, dict):
            errors.extend(review.output.get("errors", []))
            strengths.extend(review.output.get("strengths", []))
            reasons.extend(review.output.get("reasons", []))
        if cas and isinstance(cas.output, dict):
            if cas.output.get("estado_global") == "NO_VALIDADO_CAS":
                errors.append("CAS no pudo validar la afirmación matemática.")
            elif cas.output.get("estado_global") == "VALIDADO_CAS":
                strengths.append("CAS validó una o más afirmaciones.")
        if rag and not rag.evidence:
            reasons.append("No se aportó evidencia RAG.")
        consistent = not errors
        score = max(0.0, min(1.0, 1.0 - 0.2 * len(errors)))
        return Evaluation(
            consistent=consistent,
            score=score,
            errors=tuple(errors),
            strengths=tuple(strengths),
            required_retries=tuple(errors),
            recommendation="ACCEPT" if consistent else "RETRY",
            reasons=tuple(reasons),
        )

    def run(self, task: str, context: Any = None):
        strategy_id = "baseline-v1"
        history = []
        for attempt in range(self.max_retries + 1):
            answer = self.answer_agent(task, context, strategy_id, history)
            answer_result = answer if isinstance(answer, AgentResult) else AgentResult("answer_agent", answer)
            review = self.review_agent(task, answer_result.output, context, strategy_id)
            review_result = review if isinstance(review, AgentResult) else AgentResult("review_agent", review)
            cas_result = None
            if self.cas_verifier:
                cas = self.cas_verifier(task, answer_result.output)
                cas_result = cas if isinstance(cas, AgentResult) else AgentResult("cas_verifier", cas)
            rag_result = None
            if self.rag_provider:
                rag = self.rag_provider(task, context)
                rag_result = rag if isinstance(rag, AgentResult) else AgentResult(
                    "rag_provider", rag, tuple(rag) if isinstance(rag, (list, tuple)) else ()
                )

            evaluation = self._evaluate(answer_result, review_result, cas_result, rag_result)
            history.append({
                "attempt": attempt,
                "evaluation": evaluation,
                "strategy_id": strategy_id,
            })
            if evaluation.consistent:
                break
            strategy_id = f"retry-v{attempt + 2}"

        proposal = None
        if not evaluation.consistent:
            proposal = ImprovementProposal(
                target="answer_pipeline",
                reason="Repeated evaluation failures",
                strategy="strengthen_review_and_verification constraints",
                expected_effect="reduce repeated failure modes",
                tests=("same-task-regression", "negative-case-regression"),
            )
        record_id = self.fingerprint(task) + "-" + str(len(history))
        record = LearningRecord(
            record_id=record_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            task_fingerprint=self.fingerprint(task),
            agent_results=tuple(x for x in [answer_result, review_result, cas_result, rag_result] if x),
            evaluation=evaluation,
            proposal=proposal,
            strategy_id=strategy_id,
        )
        return record


def record_to_dict(record: LearningRecord):
    return json.loads(json.dumps(record, default=lambda o: o.__dict__))
