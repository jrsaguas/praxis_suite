import unittest
from task_family import classify_task_family, group_records_by_family


class TaskFamilyTests(unittest.TestCase):
    def test_explicit_family_wins(self):
        record = {"task_family": "custom_family", "metadata": {"topic": "integral"}}
        self.assertEqual(classify_task_family(record), "custom_family")

    def test_surface_does_not_mix_with_linear_algebra(self):
        records = [
            {"record_id": "s", "metadata": {"topic": "superficie", "features": ["canvas"]}},
            {"record_id": "m", "metadata": {"topic": "matriz", "features": ["vector"]}},
        ]
        groups = group_records_by_family(records)
        self.assertEqual(len(groups["surface_visualization"]), 1)
        self.assertEqual(len(groups["linear_algebra"]), 1)


if __name__ == "__main__":
    unittest.main()
