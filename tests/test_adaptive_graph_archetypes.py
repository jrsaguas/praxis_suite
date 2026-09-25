import unittest

from adaptive_agent import AdaptiveRequest
from agent_architect import AgentArchitect
from agent_catalog import AgentCatalog
from adaptive_graph import AdaptiveGraphBridge
from agent_factory import AgentFactory


class TestAdaptiveGraphArchetypes(unittest.TestCase):
    def test_reusable_agent_preserves_archetype_in_execution_spec(self):
        factory = AgentFactory()
        candidate = factory.create(
            agent_id="canvas-reusable",
            role="canvas-html specialist",
            model_id="test",
            tools=("canvas", "javascript"),
            context=("archetype:canvas_html", "representation_plan"),
            actions=("canvas_artifacts",),
            evaluation=("interaction_integrity",),
        )
        validated = factory.validate(
            candidate,
            evidence={"passed": True, "source_id": "test-eval", "checks": ["contract"]},
        )
        catalog = AgentCatalog((validated,))
        request = AdaptiveRequest(
            task="interactive geometry",
            role="canvas-html specialist",
            requirements=("canvas",),
            tools=("canvas", "javascript"),
        )
        result = AdaptiveGraphBridge(catalog=catalog).plan(request)
        dynamic = next(
            spec for spec in result.execution_plan.tasks
            if spec.agent_id == "canvas-reusable"
        )
        self.assertEqual(dynamic.agent_id, "canvas-reusable")
        self.assertEqual(
            next(
                spec.archetype_id
                for spec in [catalog.get("canvas-reusable")]
                if spec is not None
            ),
            "canvas_html",
        )


if __name__ == "__main__":
    unittest.main()
