import unittest
from types import SimpleNamespace

from nusa.agent.orchestration import (
    DeepInvestigationOrchestrator,
    DeepInvestigationResult,
    IntentResolver,
    ResearchOrchestrator,
    ResearchPlanner,
    ResearchTask,
    ToolExecutionContext,
    ToolRouter,
    ToolRegistry,
    UnsupportedIntentError,
    UnsupportedToolError,
    create_default_tool_registry,
    validate_plan,
)
from nusa.agent.synthesis import LLMResearchSynthesizer
from nusa.agent.session_memory import ResearchSessionMemory
from nusa.discovery.banks import normalize_bank_universe
from nusa.discovery.evidence import Evidence
from nusa.discovery.workflow import build_discovery_data, discover_banks
from nusa.providers.base import BankUniverseResult, CompanyData, DataSourceStatus
from nusa.providers.sectors import create_bank_data_provider


def discovery_fixture():
    return {
        "results": [
            {
                "symbol": ticker,
                "company_name": f"SAMPLE BANK {ticker}",
                "query_values": {"revenue[2024]": 100, "revenue[2025]": value},
            }
            for ticker, value in [
                ("DEMOBANK1", 110),
                ("DEMOBANK2", 108),
                ("DEMOBANK3", 112),
                ("DEMOBANK4", 105),
                ("DEMOBANK5", 200),
            ]
        ],
        "pagination": {"total_count": 5, "showing": 5, "limit": 5},
    }


class InMemoryProvider:
    def __init__(self):
        self.status = DataSourceStatus(
            mode="demo",
            source="DEMO/SAMPLE orchestration fixture",
            is_live=False,
            retrieved_at="2026-09-29T10:00:00+00:00",
            warning="DEMO/SAMPLE; not live data.",
        )
        self.universe = normalize_bank_universe(discovery_fixture())
        self.discovery = build_discovery_data(self.universe, self.status, data_mode="synthetic")
        self.company_requests = []

    def get_bank_universe(self, force_refresh=False):
        return BankUniverseResult(self.universe, self.status)

    def get_discovery_data(self, force_refresh=False):
        return self.discovery

    def get_company_data(self, ticker):
        self.company_requests.append(ticker)
        normalized = ticker.removesuffix(".JK")
        record = self.universe.frame[self.universe.frame["ticker"] == normalized].iloc[0]
        return CompanyData(ticker=ticker, data=record.dropna().to_dict(), status=self.status)


class IntentAndPlanningTests(unittest.TestCase):
    def test_resolver_maps_supported_requests_to_intents_and_idx_tickers(self):
        resolver = IntentResolver()

        self.assertEqual(resolver.resolve("Find unusual banks").intent, "DISCOVER")
        investigate = resolver.resolve("Investigate BBRI")
        self.assertEqual(investigate.intent, "INVESTIGATE")
        self.assertEqual(investigate.tickers, ("BBRI.JK",))
        compare = resolver.resolve("Compare BBRI with BBCA and BMRI")
        self.assertEqual(compare.intent, "COMPARE")
        self.assertEqual(compare.tickers, ("BBRI.JK", "BBCA.JK", "BMRI.JK"))
        self.assertEqual(
            resolver.resolve("Compare BBRI with BBCA in the market").tickers,
            ("BBRI.JK", "BBCA.JK"),
        )

    def test_resolver_rejects_unsupported_or_incomplete_intents(self):
        resolver = IntentResolver()

        with self.assertRaises(UnsupportedIntentError):
            resolver.resolve("Write a poem about markets")
        with self.assertRaises(UnsupportedIntentError):
            resolver.resolve("Compare BBRI with itself")

    def test_planner_emits_structured_investigation_plan(self):
        plan = ResearchPlanner().create_plan("Investigate BBRI")
        serialized = plan.to_dict()

        self.assertEqual(serialized["intent"], "INVESTIGATE")
        self.assertEqual(serialized["ticker"], "BBRI.JK")
        self.assertEqual(
            [task["tool"] for task in serialized["tasks"]],
            ["get_company_evidence", "calculate_trends", "compare_peer_metrics"],
        )
        self.assertTrue(all(task["purpose"] for task in serialized["tasks"]))

    def test_plan_validation_rejects_unregistered_tools(self):
        registry = create_default_tool_registry()
        plan = ResearchPlanner().create_plan("Investigate BBRI")
        plan.tasks[0] = ResearchTask("execute_python", "arbitrary code", {"code": "1+1"})

        with self.assertRaises(UnsupportedToolError):
            validate_plan(plan, registry)

    def test_plan_validation_rejects_ticker_arguments_outside_resolved_intent(self):
        registry = create_default_tool_registry()
        plan = ResearchPlanner().create_plan("Investigate BBRI")
        plan.tasks[0] = ResearchTask(
            "get_company_evidence",
            "Fetch company details and supporting evidence.",
            {"ticker": "BMRI.JK"},
        )

        with self.assertRaises(ValueError):
            validate_plan(plan, registry)

    def test_plan_validation_rejects_repeated_tool_invocations(self):
        registry = create_default_tool_registry()
        plan = ResearchPlanner().create_plan("Find unusual banks")
        plan.tasks.append(plan.tasks[0])

        with self.assertRaises(ValueError):
            validate_plan(plan, registry)


class RoutingAndOrchestrationTests(unittest.TestCase):
    def test_memory_prefers_primary_scoring_metric_over_excluded_metric(self):
        memory = ResearchSessionMemory()
        evidence = [
            Evidence(
                ticker="SUPA.JK", metric="earnings", period="2024 to 2025",
                source="SECTORS CACHED SNAPSHOT", source_endpoint="/v2/companies/",
                retrieved_at="2026-10-06T08:26:58+00:00",
                calculation="percentage change not used for scoring",
                data_mode="cached", current_value=100, previous_value=-100,
                change=200, change_unit="IDR", scoring_eligible=False,
                exclusion_reason="SIGN_TRANSITION", absolute_change=200,
            ),
            Evidence(
                ticker="SUPA.JK", metric="net_interest_income", period="2024 to 2025",
                source="SECTORS CACHED SNAPSHOT", source_endpoint="/v2/companies/",
                retrieved_at="2026-10-06T08:26:58+00:00", calculation="validated",
                data_mode="cached", current_value=200, previous_value=100,
                change=100, scoring_contribution=80,
            ),
        ]
        result = SimpleNamespace(
            plan=SimpleNamespace(intent="INVESTIGATE", tickers=("SUPA.JK",), to_dict=lambda: {}),
            outputs={}, evidence_ledger=evidence,
        )

        memory.record_run("Investigate SUPA.JK", result)

        self.assertEqual(memory.last_anomaly_metric, "net_interest_income")

    def test_router_rejects_unsupported_tools_and_unexpected_arguments(self):
        provider = InMemoryProvider()
        context = ToolExecutionContext(provider)
        router = ToolRouter(create_default_tool_registry())

        with self.assertRaises(UnsupportedToolError):
            router.route(ResearchTask("run_shell", "unsafe", {}), context)
        with self.assertRaises(ValueError):
            router.route(
                ResearchTask("get_bank_universe", "fetch", {"url": "https://evil"}),
                context,
            )

    def test_router_executes_only_registered_bank_universe_tool(self):
        provider = InMemoryProvider()
        context = ToolExecutionContext(provider)
        router = ToolRouter(create_default_tool_registry())

        output = router.route(ResearchTask("get_bank_universe", "Fetch bounded universe."), context)

        self.assertEqual(len(output.value["rows"]), 5)
        self.assertFalse(output.status.is_live)

    def test_orchestrator_runs_plan_tools_collects_evidence_and_traces_operations(self):
        provider = InMemoryProvider()
        orchestrator = ResearchOrchestrator(provider)

        result = orchestrator.run("Investigate DEMOBANK1")

        self.assertEqual(result.plan.intent, "INVESTIGATE")
        self.assertEqual(provider.company_requests, ["DEMOBANK1"])
        self.assertTrue(result.evidence_ledger.by_ticker("DEMOBANK1"))
        self.assertEqual(result.synthesis_context["data_source"]["mode"], "demo")
        self.assertEqual(result.synthesis.generation_mode, "template")
        self.assertTrue(result.synthesis.evidence_references)
        self.assertEqual(
            result.synthesis.evidence_references,
            [item.evidence_id for item in result.evidence_ledger],
        )
        events = [event.event for event in result.trace.events]
        expected_events = [
            "PLAN_CREATED",
            "PLAN_VALIDATED",
            "TOOL_STARTED",
            "TOOL_COMPLETED",
            "ANALYSIS_COMPLETED",
            "EVIDENCE_VALIDATED",
            "SYNTHESIS_CONTEXT_PREPARED",
            "SYNTHESIS_COMPLETED",
        ]
        event_positions = [events.index(event) for event in expected_events]
        self.assertEqual(event_positions, sorted(event_positions))
        self.assertNotIn("chain_of_thought", str(result.trace.to_dict()).lower())
        self.assertNotIn("Investigate DEMOBANK1", str(result.trace.to_dict()))

    def test_discover_and_compare_plans_execute_with_registered_tools(self):
        provider = InMemoryProvider()
        orchestrator = ResearchOrchestrator(provider)

        discovery = orchestrator.run("Find unusual banks")
        comparison = orchestrator.run("Compare DEMOBANK1 with DEMOBANK2 and DEMOBANK3")

        self.assertEqual(discovery.plan.intent, "DISCOVER")
        self.assertEqual(comparison.plan.intent, "COMPARE")
        self.assertIn("compare_peer_metrics", comparison.outputs)
        self.assertEqual(comparison.outputs["compare_peer_metrics"].value["tickers"], [
            "DEMOBANK1", "DEMOBANK2", "DEMOBANK3"
        ])

    def test_llm_can_resolve_only_when_deterministic_intent_parser_cannot(self):
        class PlanMock:
            def __init__(self):
                self.calls = 0

            def complete_json(self, system_prompt, user_prompt):
                self.calls += 1
                return {
                    "intent": "COMPARE",
                    "tickers": ["DEMOBANK1", "DEMOBANK2"],
                    "tasks": [{
                        "tool": "compare_peer_metrics",
                        "purpose": "Compare the requested banks.",
                        "arguments": {"tickers": ["DEMOBANK1", "DEMOBANK2"]},
                    }],
                }

        mock = PlanMock()
        result = ResearchOrchestrator(
            InMemoryProvider(), synthesizer=LLMResearchSynthesizer(mock)
        ).run("Differences between DEMOBANK1 and DEMOBANK2")

        self.assertEqual(result.plan.intent, "COMPARE")
        self.assertEqual(result.plan.tickers, ("DEMOBANK1", "DEMOBANK2"))
        self.assertEqual(result.synthesis.generation_mode, "template")
        self.assertEqual(mock.calls, 2)  # one plan proposal; synthesis response rejected safely

    def test_llm_planner_cannot_add_unknown_tools(self):
        class UnsafePlanMock:
            def complete_json(self, system_prompt, user_prompt):
                return {
                    "intent": "COMPARE",
                    "tickers": ["DEMOBANK1", "DEMOBANK2"],
                    "tasks": [{
                        "tool": "run_shell",
                        "purpose": "unsafe",
                        "arguments": {},
                    }],
                }

        orchestrator = ResearchOrchestrator(
            InMemoryProvider(), synthesizer=LLMResearchSynthesizer(UnsafePlanMock())
        )
        with self.assertRaises(UnsupportedIntentError):
            orchestrator.run("Differences between DEMOBANK1 and DEMOBANK2")

    def test_session_memory_resolves_followup_against_investigated_change(self):
        provider = InMemoryProvider()
        memory = ResearchSessionMemory()
        orchestrator = ResearchOrchestrator(provider, session_memory=memory)

        investigation = orchestrator.run("Investigate DEMOBANK1")
        comparison = orchestrator.run("Compare this change with DEMOBANK2 and DEMOBANK3")

        self.assertEqual(investigation.plan.intent, "INVESTIGATE")
        self.assertEqual(comparison.plan.intent, "COMPARE")
        self.assertEqual(comparison.plan.tickers, ("DEMOBANK1", "DEMOBANK2", "DEMOBANK3"))
        self.assertEqual(comparison.plan.tasks[0].arguments["metric"], "revenue")
        self.assertEqual(comparison.outputs["compare_peer_metrics"].value["metric"], "revenue")
        self.assertTrue(all(
            item.metric == "revenue" for item in comparison.evidence_ledger
        ))
        self.assertEqual(memory.active_ticker, "DEMOBANK1")
        self.assertEqual(memory.active_sector, "Banks")
        self.assertEqual(memory.last_investigation_objective, "Investigate DEMOBANK1")
        self.assertEqual(memory.last_anomaly_metric, "revenue")
        self.assertEqual(memory.selected_peers, ["DEMOBANK2", "DEMOBANK3"])
        self.assertEqual(memory.evidence_ids, [item.evidence_id for item in comparison.evidence_ledger])
        self.assertEqual(memory.previous_plan, comparison.plan.to_dict())

    def test_bundled_demo_journey_investigates_and_resolves_memory_comparison(self):
        provider = create_bank_data_provider("demo")
        memory = ResearchSessionMemory()
        orchestrator = ResearchOrchestrator(provider, session_memory=memory)

        discovery = orchestrator.run("Find unusual financial changes among Indonesian banks.")
        selected = discovery.outputs["discover_bank_anomalies"].value["anomalies"][0]["ticker"]
        investigation = orchestrator.run(f"Investigate {selected}")
        followup = orchestrator.run(
            "Compare this change with DEMOBANK2 and DEMOBANK3."
        )

        comparison = followup.outputs["compare_peer_metrics"].value
        self.assertEqual(selected, "DEMOBANK5")
        self.assertEqual(investigation.plan.intent, "INVESTIGATE")
        self.assertTrue(investigation.evidence_ledger.by_ticker(selected))
        self.assertEqual(followup.plan.intent, "COMPARE")
        self.assertEqual(
            followup.plan.tickers,
            ("DEMOBANK5", "DEMOBANK2", "DEMOBANK3"),
        )
        expected_metric = discovery.outputs["discover_bank_anomalies"].value["anomalies"][0]["primary_driver"]
        self.assertEqual(followup.plan.tasks[0].arguments["metric"], expected_metric)
        self.assertEqual(comparison["metric"], expected_metric)
        self.assertEqual(
            {item.ticker for item in followup.evidence_ledger},
            {"DEMOBANK5", "DEMOBANK2", "DEMOBANK3"},
        )
        self.assertTrue(all(item.metric == expected_metric for item in followup.evidence_ledger))
        self.assertEqual(memory.last_anomaly_metric, expected_metric)
        self.assertEqual(memory.selected_peers, ["DEMOBANK2", "DEMOBANK3"])

    def test_session_memory_is_reused_from_session_state(self):
        session_state = {}
        first = ResearchSessionMemory.from_session_state(session_state)
        first.active_ticker = "BBRI.JK"

        second = ResearchSessionMemory.from_session_state(session_state)

        self.assertIs(first, second)
        self.assertEqual(second.active_ticker, "BBRI.JK")
        self.assertEqual(set(first.to_dict()), {
            "active_ticker",
            "active_sector",
            "last_investigation_objective",
            "last_anomaly_metric",
            "selected_peers",
            "evidence_ids",
            "previous_plan",
        })

    def test_registry_is_explicit_and_does_not_evaluate_tool_names(self):
        registry = ToolRegistry()
        with self.assertRaises(UnsupportedToolError):
            registry.get("__import__('os').system('whoami')")

    def test_answer_followup_succeeds_on_valid_evidence(self):
        provider = InMemoryProvider()
        orchestrator = ResearchOrchestrator(provider)
        investigation = orchestrator.run("Investigate DEMOBANK5")
        synthesis = orchestrator.answer_followup(
            "What is the key takeaway?", investigation
        )
        self.assertIsNotNone(synthesis)
        self.assertTrue(bool(synthesis.executive_summary))

    def test_deep_investigation_orchestrator_runs_and_records_decisions(self):
        provider = InMemoryProvider()
        orchestrator = DeepInvestigationOrchestrator(provider)
        discovery_rows = provider.discovery.ranked.to_dict(orient="records")

        result = orchestrator.run_deep("DEMOBANK5", discovery_rows)

        self.assertIsInstance(result, DeepInvestigationResult)
        self.assertEqual(result.ticker, "DEMOBANK5")
        self.assertGreater(len(result.decisions), 0)
        self.assertIsNotNone(result.synthesis)
        self.assertTrue(bool(result.synthesis.executive_summary))
        self.assertIsInstance(result.decision_log, list)
        self.assertGreater(len(result.decision_log), 0)
        first_decision = result.decision_log[0]
        self.assertIn("step", first_decision)
        self.assertIn("observation", first_decision)
        self.assertIn("decision", first_decision)
        self.assertIn("reason", first_decision)
        events = [e.event for e in result.trace.events]
        self.assertIn("DEEP_INVESTIGATION_STARTED", events)
        self.assertIn("DEEP_INVESTIGATION_COMPLETED", events)

    def test_tool_get_company_evidence_falls_back_when_company_report_fails(self):
        provider = InMemoryProvider()
        def fail_get_company_data(ticker):
            raise RuntimeError("401 Unauthorized simulated")
        provider.get_company_data = fail_get_company_data

        orchestrator = ResearchOrchestrator(provider)
        investigation = orchestrator.run("Investigate DEMOBANK1")
        self.assertEqual(investigation.resolved_intent.intent, "INVESTIGATE")
        company_output = investigation.outputs["get_company_evidence"]
        self.assertIn("screener_row", company_output.value["company"])
        self.assertIn("fallback", company_output.status.source)


if __name__ == "__main__":
    unittest.main()
