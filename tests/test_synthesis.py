import os
import unittest
from unittest.mock import patch

from nusa.agent.synthesis import (
    LLMResearchSynthesizer,
    OpenAICompatibleLLMProvider,
    ResearchSynthesis,
    create_llm_provider_from_env,
)
from nusa.discovery.evidence import Evidence, EvidenceLedger


def sample_ledger():
    return EvidenceLedger([
        Evidence(
            evidence_id="ev-001",
            ticker="DEMOBANK1",
            company_name="Sample Bank",
            metric="revenue",
            current_value=120,
            previous_value=100,
            change=20,
            peer_median=5,
            peer_count=4,
            deviation=15,
            period="2024 to 2025",
            source="DEMO/SAMPLE fixture",
            source_endpoint="fixture://banks",
            retrieved_at="2026-09-29T10:00:00+00:00",
            calculation="sample calculation",
            data_mode="synthetic",
        )
    ])


class MockLLMProvider:
    def __init__(self, response=None):
        self.response = response or {
            "executive_summary": "DEMOBANK1 revenue changed by 20% [ev-001].",
            "key_findings": ["The observed change was 20% [ev-001]."],
            "historical_context": ["2024 to 2025 [ev-001]."],
            "peer_comparison": ["Peer median change was 5% [ev-001]."],
            "why_flagged": ["Deviation was 15 percentage points [ev-001]."],
            "limitations": ["Values are synthetic sample data."],
            "evidence_references": ["ev-001"],
        }
        self.calls = []

    def complete_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


class SynthesisTests(unittest.TestCase):
    def test_no_provider_generates_deterministic_evidence_cited_summary(self):
        result = LLMResearchSynthesizer().synthesize(
            "Investigate DEMOBANK1", {"intent": "INVESTIGATE"}, sample_ledger()
        )

        self.assertIsInstance(result, ResearchSynthesis)
        self.assertEqual(result.generation_mode, "template")
        self.assertEqual(result.evidence_references, ["ev-001"])
        self.assertIn("20", result.executive_summary)
        self.assertTrue(result.limitations)

    def test_mock_provider_synthesizes_with_required_safety_prompt(self):
        provider = MockLLMProvider()
        result = LLMResearchSynthesizer(provider).synthesize(
            "Investigate DEMOBANK1", {"intent": "INVESTIGATE"}, sample_ledger()
        )

        self.assertEqual(result.generation_mode, "llm")
        self.assertEqual(provider.calls.__len__(), 1)
        prompt = " ".join(provider.calls[0])
        for requirement in ("BUY", "SELL", "fraud", "evidence", "invent"):
            self.assertIn(requirement.lower(), prompt.lower())

    def test_unreferenced_or_novel_numeric_claim_falls_back_to_template(self):
        response = MockLLMProvider().response
        response["executive_summary"] = "DEMOBANK1 revenue is 999% [ev-001]."
        provider = MockLLMProvider(response)

        result = LLMResearchSynthesizer(provider).synthesize(
            "Investigate DEMOBANK1", {"intent": "INVESTIGATE"}, sample_ledger()
        )

        self.assertEqual(result.generation_mode, "template")
        self.assertTrue(any("unsupported numeric" in item.lower() for item in result.limitations))

    def test_unknown_evidence_reference_falls_back(self):
        response = MockLLMProvider().response
        response["evidence_references"] = ["made-up-id"]
        result = LLMResearchSynthesizer(MockLLMProvider(response)).synthesize(
            "Investigate DEMOBANK1", {"intent": "INVESTIGATE"}, sample_ledger()
        )
        self.assertEqual(result.generation_mode, "template")

    def test_followup_without_provider_does_not_call_external_service(self):
        synthesizer = LLMResearchSynthesizer()
        answer = synthesizer.answer_followup("What changed?", sample_ledger(), None)
        self.assertEqual(answer.generation_mode, "template")
        self.assertIn("validated evidence", answer.executive_summary.lower())

    def test_provider_configuration_is_environment_driven_and_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(create_llm_provider_from_env())
        config = {
            "NUSA_LLM_API_KEY": "test-not-a-real-key",
            "NUSA_LLM_BASE_URL": "https://api.example.test/v1",
            "NUSA_LLM_MODEL": "mock-model",
        }
        with patch.dict(os.environ, config, clear=True):
            provider = create_llm_provider_from_env()
        self.assertIsInstance(provider, OpenAICompatibleLLMProvider)
        self.assertEqual(provider.model, "mock-model")

    def test_partial_provider_configuration_fails_closed_without_echoing_key(self):
        config = {"NUSA_LLM_API_KEY": "do-not-print-this"}
        with patch.dict(os.environ, config, clear=True):
            with self.assertRaises(ValueError) as raised:
                create_llm_provider_from_env()
        self.assertNotIn("do-not-print-this", str(raised.exception))

if __name__ == "__main__":
    unittest.main()
