import unittest

from benchmarks.suites.belief_shadow_gate import assess_case


class BeliefShadowGateTests(unittest.TestCase):
    def base(self):
        return {
            "case_id": "x",
            "source_kind": "fixture",
            "candidate": {
                "scope": "lab",
                "temporal_scope": "during trial",
                "evidence_quote": "quoted source",
                "source_text": "quoted source",
            },
            "comparisons": {},
            "diagnostics": [
                {
                    "question_id": "factual_grounding",
                    "choice": "unsupported",
                    "confidence": 0.98,
                    "status": "within_threshold",
                },
                {"question_id": "tension", "choice": "present", "confidence": 0.54, "status": "below_threshold"},
            ],
            "context_issues": [],
            "legacy_assessment": "abstained",
        }

    def test_v29_keeps_confident_dimensions_separate_without_adoption(self):
        result = assess_case(self.base())
        self.assertFalse(result["legacy_aggregate_gate_passed"])
        self.assertEqual([x["dimension"] for x in result["shadow_retained"]], ["factual_grounding"])
        self.assertEqual(result["shadow_retained"][0]["choice"], "unsupported")
        self.assertEqual(result["unresolved"][0]["status"], "unresolved")
        self.assertEqual(result["adoption_authority"], "none")

    def test_v29_unbound_candidate_quote_blocks_every_dimension(self):
        case = self.base()
        case["candidate"]["evidence_quote"] = "not present"
        result = assess_case(case)
        self.assertFalse(result["candidate_context_valid"])
        self.assertEqual(result["shadow_retained"], [])
        self.assertTrue(all(x["reason"] == "candidate_context_or_quote_unbound" for x in result["unresolved"]))

    def test_v29_relation_requires_matching_bounded_peer_context(self):
        case = self.base()
        case["diagnostics"].append(
            {"question_id": "relation_0", "choice": "contradiction", "confidence": 0.91, "status": "within_threshold"}
        )
        case["comparisons"]["relation_0"] = {
            "scope": "lab",
            "temporal_scope": "before trial",
            "evidence_quote": "peer quote",
            "source_text": "peer quote",
        }
        result = assess_case(case)
        relation = next(x for x in result["unresolved"] if x["dimension"] == "relation_0")
        self.assertEqual(relation["reason"], "comparison_context_or_quote_unbound")

    def test_v29_missing_confidence_is_unresolved(self):
        case = self.base()
        case["diagnostics"][0]["confidence"] = None
        result = assess_case(case)
        self.assertEqual(result["shadow_retained"], [])

    def test_v29_insufficient_relation_is_unresolved_even_at_floor(self):
        case = self.base()
        case["diagnostics"].append(
            {"question_id": "relation_0", "choice": "insufficient", "confidence": 0.99, "status": "within_threshold"}
        )
        case["comparisons"]["relation_0"] = {"scope": "lab", "temporal_scope": "during trial"}
        result = assess_case(case)
        relation = next(x for x in result["unresolved"] if x["dimension"] == "relation_0")
        self.assertEqual(relation["reason"], "noncommittal_relation_choice")

    def test_v29_unclear_dimension_is_unresolved_even_at_floor(self):
        case = self.base()
        case["diagnostics"][0].update(choice="unclear", confidence=0.99, status="within_threshold")
        result = assess_case(case)
        factual = next(x for x in result["unresolved"] if x["dimension"] == "factual_grounding")
        self.assertEqual(factual["reason"], "noncommittal_dimension_choice")


if __name__ == "__main__":
    unittest.main()
