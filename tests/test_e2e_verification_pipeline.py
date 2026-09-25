import unittest

from agent_architecture import get_agent
from agent_graph import AgentGraphPlanner, AgentTask, ExecutionPlan
from agent_runtime import AgentRuntime
from agent_gate_verifiers import verify_output


def _subset_plan(plan, agent_ids):
    selected = set(agent_ids)
    tasks = tuple(
        task for task in plan.tasks
        if task.agent_id in selected
    )
    # Keep only dependencies that remain in the focused E2E slice.
    focused = tuple(
        AgentTask(
            task_id=task.task_id,
            agent_id=task.agent_id,
            inputs=task.inputs,
            outputs=task.outputs,
            depends_on=tuple(dep for dep in task.depends_on if dep in {t.task_id for t in tasks}),
            quality_gates=task.quality_gates,
            status=task.status,
            model_id=task.model_id,
            archetype_id=task.archetype_id,
            required_tools=task.required_tools,
            optional_tools=task.optional_tools,
            model_capabilities=task.model_capabilities,
            depth_requirements=task.depth_requirements,
            delivery_gates=task.delivery_gates,
            missing_tools=task.missing_tools,
            depth_gaps=task.depth_gaps,
        )
        for task in tasks
    )
    return ExecutionPlan(focused, tuple(t.agent_id for t in focused))


def _contract(task):
    return {
        "gate_results": {
            gate: {"passed": True, "evidence": f"fixture:{gate}"}
            for gate in (*task.quality_gates, *task.delivery_gates)
        }
    }


class EndToEndVerificationPipelineTests(unittest.TestCase):
    def test_mathematical_chain_reaches_proof_only_after_independent_cas(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["mathematical_resolver"],
            depth_requirements={"proof": 80},
        )
        focused = _subset_plan(
            plan,
            [
                "intent_router",
                "architect",
                "foundation_analyst",
                "mathematical_resolver",
                "proof_specialist",
            ],
        )
        executed = []

        def execute(task, context):
            executed.append(task.agent_id)
            if task.agent_id == "mathematical_resolver":
                return {
                    "solution": "(x + 1)^2 = x^2 + 2*x + 1",
                    "derivation": "Expansión del cuadrado.",
                    "assumptions": ["x es real"],
                    "verification_certificate": {
                        "claim_type": "identity",
                        "variables": ["x"],
                        "lhs": "(x + 1)**2",
                        "rhs": "x**2 + 2*x + 1",
                    },
                }
            return _contract(task)

        trace = AgentRuntime(execute, max_retries=0).run(focused, {"user_prompt": "Expandir (x+1)^2."})

        self.assertEqual(trace.status, "completed")
        self.assertEqual(executed[-2:], ["mathematical_resolver", "proof_specialist"])
        resolver = next(r for r in trace.results if r.agent_id == "mathematical_resolver")
        evidence = resolver.delivery["evidence"]["symbolic_consistency"]
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["verified_by"], "independent_cas")
        self.assertIn("proof_specialist", trace.completed)

    def test_false_cas_claim_blocks_proof_and_publishes_no_resolver_artifact(self):
        plan = AgentGraphPlanner().plan(
            requested_agents=["mathematical_resolver"],
            depth_requirements={"proof": 80},
        )
        focused = _subset_plan(
            plan,
            [
                "intent_router",
                "architect",
                "foundation_analyst",
                "mathematical_resolver",
                "proof_specialist",
            ],
        )
        executed = []

        def execute(task, context):
            executed.append(task.agent_id)
            if task.agent_id == "mathematical_resolver":
                return {
                    "solution": "x + 1 = x + 2",
                    "derivation": "Afirmación deliberadamente falsa.",
                    "assumptions": [],
                    "verification_certificate": {
                        "claim_type": "identity",
                        "variables": ["x"],
                        "lhs": "x + 1",
                        "rhs": "x + 2",
                    },
                }
            return _contract(task)

        trace = AgentRuntime(execute, max_retries=0).run(focused)
        resolver = next(r for r in trace.results if r.agent_id == "mathematical_resolver")

        self.assertEqual(trace.status, "failed")
        self.assertIn("mathematical_resolver", executed)
        self.assertNotIn("proof_specialist", executed)
        self.assertNotIn("mathematical_resolver", trace.artifacts)
        self.assertIn("symbolic_consistency", resolver.delivery["failed_gates"])

    def test_model_self_reported_verified_gate_cannot_bypass_real_verifier(self):
        task = AgentTask(
            task_id="task:mathematical_resolver",
            agent_id="mathematical_resolver",
            inputs=(),
            outputs=("solution",),
            depends_on=(),
            quality_gates=(),
            delivery_gates=("symbolic_consistency",),
        )
        result = verify_output(task, {
            "verification_certificate": {"passed": True},
            "verified_gates": {"symbolic_consistency": {"passed": True}},
            "evidence_provenance": {
                "origin": "model_self_report",
                "authoritative": False,
            },
        }, "delivery")
        self.assertFalse(result.passed)
        self.assertIn("symbolic_consistency", result.missing_gates)

    def test_research_fabricated_source_without_retriever_provenance_is_blocked(self):
        spec = get_agent("research_specialist")
        task = AgentTask(
            task_id="task:research_specialist",
            agent_id=spec.id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            depends_on=(),
            quality_gates=spec.quality_gates,
            delivery_gates=spec.delivery_gates,
            archetype_id=spec.archetype_id,
            required_tools=spec.required_tools,
            optional_tools=spec.optional_tools,
            model_capabilities=spec.model_capabilities,
            depth_requirements=spec.depth_requirements,
        )
        output = {
            "retrieved_sources": [{
                "title": "Invented source",
                "year": "2026",
                "abstract": "Not retrieved.",
                "pdf_url": "https://example.invalid/fake.pdf",
            }],
            "source_map": [{"claim": "C1", "source_title": "Invented source"}],
            "citations": [{"title": "Invented source", "url": "https://example.invalid/fake.pdf"}],
        }
        result = verify_output(task, output, "delivery")
        self.assertFalse(result.passed)
        self.assertIn("source_traceability", result.failed_gates)

    def test_research_claim_source_mismatch_is_blocked(self):
        spec = get_agent("research_specialist")
        task = AgentTask(
            task_id="task:research_specialist",
            agent_id=spec.id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            depends_on=(),
            quality_gates=spec.quality_gates,
            delivery_gates=spec.delivery_gates,
            archetype_id=spec.archetype_id,
            required_tools=spec.required_tools,
            optional_tools=spec.optional_tools,
            model_capabilities=spec.model_capabilities,
            depth_requirements=spec.depth_requirements,
        )
        retrieved = [{
            "title": "Verified source",
            "year": "2026",
            "abstract": "Retrieved evidence.",
            "pdf_url": "https://arxiv.org/pdf/1234.5678",
            "retrieved_by": "rag_engine.search_arxiv",
        }]
        result = verify_output(task, {
            "retrieved_sources": retrieved,
            "source_map": [{"claim": "C1", "source_title": "Different source"}],
            "citations": [{"title": "Different source", "url": "https://example.invalid/other.pdf"}],
        }, "delivery")
        self.assertFalse(result.passed)
        self.assertIn("claim_support", result.failed_gates)

    def test_research_valid_retriever_evidence_passes_traceability_and_claim_support(self):
        spec = get_agent("research_specialist")
        task = AgentTask(
            task_id="task:research_specialist",
            agent_id=spec.id,
            inputs=spec.inputs,
            outputs=spec.outputs,
            depends_on=(),
            quality_gates=spec.quality_gates,
            delivery_gates=spec.delivery_gates,
            archetype_id=spec.archetype_id,
            required_tools=spec.required_tools,
            optional_tools=spec.optional_tools,
            model_capabilities=spec.model_capabilities,
            depth_requirements=spec.depth_requirements,
        )
        retrieved = [{
            "title": "Verified source",
            "year": "2026",
            "abstract": "Retrieved evidence.",
            "pdf_url": "https://arxiv.org/pdf/1234.5678",
            "retrieved_by": "rag_engine.search_arxiv",
        }]
        result = verify_output(task, {
            "retrieved_sources": retrieved,
            "source_map": [{"claim": "C1", "source_title": "Verified source"}],
            "citations": [{"title": "Verified source", "url": "https://arxiv.org/pdf/1234.5678"}],
        }, "delivery")
        self.assertTrue(result.passed)
        self.assertFalse(result.failed_gates)
        self.assertFalse(result.missing_gates)


if __name__ == "__main__":
    unittest.main()
