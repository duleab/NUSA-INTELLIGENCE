"""Small deterministic agent loop with an explicit safe-tool allowlist.

This module intentionally has no LLM or code-execution integration. Plans are
created from fixed templates and operational traces omit internal reasoning.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from nusa.discovery.evidence import Evidence, EvidenceLedger, EvidenceValidator
from nusa.agent.synthesis import LLMResearchSynthesizer, ResearchSynthesis
from nusa.agent.session_memory import ResearchSessionMemory
from nusa.providers.base import BankDataProvider, DataSourceStatus


_TICKER_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{3,20}(?:\.JK)?)(?![A-Z0-9])", re.IGNORECASE)
_TICKER_STOPWORDS = {
    "AGAINST", "AND", "ANOMALIES", "ANOMALY", "ABOUT", "BANK", "BANKS", "CALCULATE",
    "COMPARE", "COMPANIES", "COMPANY", "DATA", "DISCOVER", "FIND", "FINANCIAL",
    "FINANCIALS", "FOR", "INVESTIGATE", "INVESTIGATION", "ITSELF", "MARKET", "MARKETS",
    "ME", "METRIC", "METRICS", "PEER", "PEERS", "PLEASE", "RESEARCH", "SCREEN",
    "SCREENING", "SHOW", "THE", "TRENDS", "TREND", "UNUSUAL", "VERSUS", "WHAT",
    "WHICH", "WITH", "DIFFERENCES", "BETWEEN", "DIFFERENT", "CONTRAST", "RELATIVE",
    "PERFORM", "BETTER", "WORSE", "EACH", "OTHER", "HOW", "DOES",
}
_DISCOVER_TERMS = re.compile(r"\b(discover|find|screen|unusual|anomal(?:y|ies)?|banks?)\b", re.I)
_INVESTIGATE_TERMS = re.compile(
    r"\b(investigate|investigation|research|analy[sz]e|inspect|explain)\b", re.I
)
_COMPARE_TERMS = re.compile(r"\b(compare|versus|vs\.?|against)\b", re.I)
_ALLOWED_INTENTS = {"DISCOVER", "INVESTIGATE", "COMPARE"}
_REQUIRED_TOOLS = {
    "DISCOVER": {"discover_bank_anomalies"},
    "INVESTIGATE": {"get_company_evidence", "calculate_trends", "compare_peer_metrics"},
    "COMPARE": {"compare_peer_metrics"},
}


class UnsupportedIntentError(ValueError):
    """The request is outside the deliberately small supported intent set."""


class UnsupportedToolError(ValueError):
    """A plan attempted to route a tool that is not explicitly registered."""


class PlanValidationError(ValueError):
    """A structured research plan violates the supported schema or policy."""


class EvidenceValidationError(ValueError):
    """A research result contains evidence that failed deterministic validation."""


@dataclass(frozen=True)
class ResolvedIntent:
    intent: str
    tickers: tuple[str, ...] = ()


class IntentResolver:
    """Resolve the three MVP intents using explicit phrase and ticker rules."""

    def resolve(self, request: str) -> ResolvedIntent:
        if not isinstance(request, str) or not request.strip():
            raise UnsupportedIntentError("Request must be a non-empty string")
        tickers = _extract_tickers(request)
        if _COMPARE_TERMS.search(request):
            if len(tickers) < 2:
                raise UnsupportedIntentError("COMPARE requires at least two distinct tickers")
            return ResolvedIntent("COMPARE", tickers)
        if _INVESTIGATE_TERMS.search(request):
            if len(tickers) != 1:
                raise UnsupportedIntentError("INVESTIGATE requires exactly one ticker")
            return ResolvedIntent("INVESTIGATE", tickers)
        if _DISCOVER_TERMS.search(request):
            return ResolvedIntent("DISCOVER")
        raise UnsupportedIntentError("Supported intents are DISCOVER, INVESTIGATE, and COMPARE")


@dataclass(frozen=True)
class ResearchTask:
    tool: str
    purpose: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "purpose": self.purpose, "arguments": dict(self.arguments)}


@dataclass
class ResearchPlan:
    objective: str
    intent: str
    ticker: str | None
    tasks: list[ResearchTask]
    tickers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "intent": self.intent,
            "ticker": self.ticker,
            "tickers": list(self.tickers),
            "tasks": [task.to_dict() for task in self.tasks],
        }


class ResearchPlanner:
    """Create fixed, inspectable plans; there is no model-generated planning."""

    def __init__(self, resolver: IntentResolver | None = None) -> None:
        self.resolver = resolver or IntentResolver()

    def create_plan(
        self,
        request: str,
        resolved: ResolvedIntent | None = None,
    ) -> ResearchPlan:
        intent = resolved or self.resolver.resolve(request)
        ticker = intent.tickers[0] if intent.tickers else None
        if intent.intent == "DISCOVER":
            tasks = [
                ResearchTask(
                    "discover_bank_anomalies",
                    "Rank unusual patterns from the bounded bank universe and its evidence.",
                )
            ]
        elif intent.intent == "INVESTIGATE":
            tasks = [
                ResearchTask(
                    "get_company_evidence",
                    "Fetch company details and supporting evidence.",
                    {"ticker": ticker},
                ),
                ResearchTask(
                    "calculate_trends",
                    "Return deterministic trend evidence already computed by Discovery.",
                    {"ticker": ticker},
                ),
                ResearchTask(
                    "compare_peer_metrics",
                    "Compare metrics with their recorded peer baselines.",
                    {"tickers": [ticker]},
                ),
            ]
        elif intent.intent == "COMPARE":
            tasks = [
                ResearchTask(
                    "compare_peer_metrics",
                    "Compare the selected banks using same-period evidence and peer baselines.",
                    {"tickers": list(intent.tickers)},
                )
            ]
        else:
            raise UnsupportedIntentError(f"Unsupported intent: {intent.intent}")
        return ResearchPlan(
            objective=request.strip(),
            intent=intent.intent,
            ticker=ticker,
            tickers=intent.tickers,
            tasks=tasks,
        )


@dataclass(frozen=True)
class TraceEvent:
    event: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    events: list[TraceEvent] = field(default_factory=list)

    def record(self, event: str, **details: Any) -> None:
        self.events.append(
            TraceEvent(
                event=event,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details=details,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {"events": [asdict(event) for event in self.events]}


@dataclass(frozen=True)
class ToolOutput:
    value: Any
    evidence: tuple[Evidence, ...]
    status: DataSourceStatus


@dataclass
class ToolExecutionContext:
    provider: BankDataProvider
    cache: dict[str, Any] = field(default_factory=dict)

    def discovery_data(self):
        if "discovery_data" not in self.cache:
            self.cache["discovery_data"] = self.provider.get_discovery_data()
        return self.cache["discovery_data"]


ToolHandler = Callable[..., ToolOutput]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    handler: ToolHandler
    required_arguments: frozenset[str]
    allowed_arguments: frozenset[str]


class ToolRegistry:
    """Explicit safe-tool map; names are looked up, never interpreted as code."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: ToolHandler,
        *,
        required_arguments: Iterable[str] = (),
        allowed_arguments: Iterable[str] | None = None,
    ) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError("Tool names must be lowercase identifiers")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        required = frozenset(required_arguments)
        allowed = required if allowed_arguments is None else frozenset(allowed_arguments)
        if not required <= allowed:
            raise ValueError("Required tool arguments must be allowed arguments")
        self._tools[name] = ToolDefinition(name, handler, required, allowed)

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError:
            raise UnsupportedToolError(f"Unsupported tool: {name}") from None

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> None:
        definition = self.get(name)
        if not isinstance(arguments, dict):
            raise PlanValidationError(f"Arguments for {name} must be an object")
        missing = definition.required_arguments - arguments.keys()
        unexpected = arguments.keys() - definition.allowed_arguments
        if missing:
            raise PlanValidationError(f"Missing arguments for {name}: {sorted(missing)}")
        if unexpected:
            raise PlanValidationError(f"Unexpected arguments for {name}: {sorted(unexpected)}")


class ToolRouter:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def route(self, task: ResearchTask, context: ToolExecutionContext) -> ToolOutput:
        definition = self.registry.get(task.tool)
        self.registry.validate_arguments(task.tool, task.arguments)
        return definition.handler(context, **task.arguments)


def validate_plan(plan: ResearchPlan, registry: ToolRegistry) -> None:
    if plan.intent not in _ALLOWED_INTENTS:
        raise UnsupportedIntentError(f"Unsupported intent: {plan.intent}")
    if not plan.objective.strip() or not plan.tasks:
        raise PlanValidationError("Plan requires an objective and at least one task")
    if plan.ticker is not None and not _is_ticker(plan.ticker):
        raise PlanValidationError("Plan ticker must be a valid ticker string")
    if not isinstance(plan.tickers, (tuple, list)) or not all(
        _is_ticker(ticker) for ticker in plan.tickers
    ):
        raise PlanValidationError("Plan tickers must be valid ticker strings")
    planned_tools: set[str] = set()
    for task in plan.tasks:
        registry.validate_arguments(task.tool, task.arguments)
        if not isinstance(task.purpose, str) or not task.purpose.strip():
            raise PlanValidationError(f"Task purpose is required for {task.tool}")
        if task.tool in planned_tools:
            raise PlanValidationError(f"Repeated tool invocation is not allowed: {task.tool}")
        if "ticker" in task.arguments and not _is_ticker(task.arguments["ticker"]):
            raise PlanValidationError(f"{task.tool} requires a valid ticker string")
        if "tickers" in task.arguments:
            tickers = task.arguments["tickers"]
            if not isinstance(tickers, list) or not tickers or not all(
                _is_ticker(ticker) for ticker in tickers
            ):
                raise PlanValidationError(f"{task.tool} requires a non-empty ticker list")
        planned_tools.add(task.tool)
    missing_tools = _REQUIRED_TOOLS[plan.intent] - planned_tools
    if missing_tools:
        raise PlanValidationError(f"Plan omits required tools: {sorted(missing_tools)}")
    unexpected_tools = planned_tools - _REQUIRED_TOOLS[plan.intent]
    if unexpected_tools:
        raise PlanValidationError(
            f"Tools are not valid for {plan.intent}: {sorted(unexpected_tools)}"
        )
    if plan.intent == "INVESTIGATE":
        if not plan.ticker or len(plan.tickers) != 1:
            raise PlanValidationError("INVESTIGATE plans require one ticker")
        if plan.ticker != plan.tickers[0]:
            raise PlanValidationError("Plan ticker does not match its resolved ticker list")
        for task in plan.tasks:
            if "ticker" in task.arguments and task.arguments["ticker"] != plan.ticker:
                raise PlanValidationError("Task ticker does not match the resolved intent")
            if (
                task.tool == "compare_peer_metrics"
                and task.arguments.get("tickers") != [plan.ticker]
            ):
                raise PlanValidationError(
                    "Investigation peer comparison must use its resolved ticker"
                )
    if plan.intent == "COMPARE":
        if (
            len(plan.tickers) < 2
            or len({_ticker_key(t) for t in plan.tickers}) != len(plan.tickers)
        ):
            raise PlanValidationError("COMPARE plans require at least two distinct tickers")
        if plan.ticker != plan.tickers[0]:
            raise PlanValidationError("Plan ticker must be the first resolved comparison ticker")
        for task in plan.tasks:
            if (
                task.tool == "compare_peer_metrics"
                and task.arguments.get("tickers") != list(plan.tickers)
            ):
                raise PlanValidationError("Comparison arguments do not match resolved tickers")


class ResearchOrchestrator:
    """Execute deterministic plans, retain validated evidence, and expose trace."""

    def __init__(
        self,
        provider: BankDataProvider,
        *,
        registry: ToolRegistry | None = None,
        resolver: IntentResolver | None = None,
        planner: ResearchPlanner | None = None,
        validator: EvidenceValidator | None = None,
        synthesizer: LLMResearchSynthesizer | None = None,
        session_memory: ResearchSessionMemory | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry or create_default_tool_registry()
        self.resolver = resolver or IntentResolver()
        self.planner = planner or ResearchPlanner(self.resolver)
        self.validator = validator or EvidenceValidator()
        self.synthesizer = synthesizer or LLMResearchSynthesizer()
        self.session_memory = session_memory
        self.router = ToolRouter(self.registry)
        self.last_trace = ExecutionTrace()

    def run(self, request: str) -> ResearchRunResult:
        effective_request = (
            self.session_memory.resolve_request(request) if self.session_memory else request
        )
        trace = ExecutionTrace()
        self.last_trace = trace
        trace.record(
            "REQUEST_RECEIVED",
            request_characters=len(request) if isinstance(request, str) else 0,
        )
        try:
            resolved = self.resolver.resolve(effective_request)
            model_plan = None
        except UnsupportedIntentError as error:
            try:
                resolved, model_plan = self.synthesizer.plan_from_request(
                    effective_request, self.registry
                )
                trace.record("INTENT_RESOLVED", intent=resolved.intent, ticker_count=len(resolved.tickers))
                trace.record("PLAN_CREATED", intent=model_plan.intent, tools=[task.tool for task in model_plan.tasks], task_count=len(model_plan.tasks), planner="llm")
            except Exception:
                trace.record("INTENT_REJECTED", error_type=type(error).__name__)
                raise error from None
        except Exception as error:
            trace.record("INTENT_REJECTED", error_type=type(error).__name__)
            raise
        if model_plan is None:
            trace.record("INTENT_RESOLVED", intent=resolved.intent, ticker_count=len(resolved.tickers))
            plan = self.planner.create_plan(effective_request, resolved)
            trace.record(
                "PLAN_CREATED",
                intent=plan.intent,
                tools=[task.tool for task in plan.tasks],
                task_count=len(plan.tasks),
            )
        else:
            plan = model_plan
        if self.session_memory and self.session_memory.is_change_followup(request):
            for task in plan.tasks:
                if task.tool == "compare_peer_metrics":
                    task.arguments["metric"] = self.session_memory.last_anomaly_metric
        try:
            if plan.intent != resolved.intent or plan.tickers != resolved.tickers:
                raise PlanValidationError("Planner output does not match the resolved request")
            validate_plan(plan, self.registry)
        except Exception as error:
            trace.record("PLAN_REJECTED", error_type=type(error).__name__)
            raise
        trace.record("PLAN_VALIDATED", task_count=len(plan.tasks))

        context = ToolExecutionContext(self.provider)
        outputs: dict[str, ToolOutput] = {}
        ledger = EvidenceLedger()
        for task in plan.tasks:
            trace.record("TOOL_STARTED", tool=task.tool)
            try:
                output = self.router.route(task, context)
            except Exception as error:
                trace.record("TOOL_FAILED", tool=task.tool, error_type=type(error).__name__)
                raise
            outputs[task.tool] = output
            for evidence in output.evidence:
                if evidence.evidence_id not in {item.evidence_id for item in ledger}:
                    ledger.add(evidence)
            trace.record(
                "TOOL_COMPLETED",
                tool=task.tool,
                result_type=type(output.value).__name__,
                evidence_count=len(output.evidence),
                data_mode=output.status.mode,
            )

        trace.record("ANALYSIS_COMPLETED", tool_count=len(outputs), evidence_count=len(ledger))
        validation_errors = {
            evidence.evidence_id: errors
            for evidence in ledger
            if (errors := self.validator.validate(evidence))
        }
        trace.record(
            "EVIDENCE_VALIDATED",
            evidence_count=len(ledger),
            valid=not validation_errors,
            invalid_count=len(validation_errors),
        )
        if validation_errors:
            raise EvidenceValidationError(
                f"Evidence validation failed for {len(validation_errors)} records"
            )

        status = self.provider.status
        synthesis_context = {
            "data_source": asdict(status),
            **ledger.to_llm_context(),
        }
        trace.record("SYNTHESIS_CONTEXT_PREPARED", evidence_count=len(ledger))
        synthesis = self.synthesizer.synthesize(
            effective_request,
            plan.to_dict(),
            ledger,
            data_source=asdict(status),
        )
        trace.record(
            "SYNTHESIS_COMPLETED",
            generation_mode=synthesis.generation_mode,
            evidence_reference_count=len(synthesis.evidence_references),
        )
        result = ResearchRunResult(
            resolved_intent=resolved,
            plan=plan,
            outputs=outputs,
            evidence_ledger=ledger,
            synthesis_context=synthesis_context,
            synthesis=synthesis,
            trace=trace,
        )
        if self.session_memory:
            self.session_memory.record_run(request, result)
            trace.record("SESSION_MEMORY_UPDATED", field_count=7)
        return result

    def answer_followup(self, question: str, previous: ResearchRunResult) -> ResearchSynthesis:
        """Answer against a prior run's validated ledger; this does not fetch new data."""
        if previous.evidence_ledger.validate():
            raise EvidenceValidationError("Prior evidence failed validation")
        return self.synthesizer.answer_followup(
            question,
            previous.evidence_ledger,
            previous.synthesis,
            data_source=previous.synthesis_context.get("data_source"),
        )


@dataclass(frozen=True)
class ResearchRunResult:
    resolved_intent: ResolvedIntent
    plan: ResearchPlan
    outputs: dict[str, ToolOutput]
    evidence_ledger: EvidenceLedger
    synthesis_context: dict[str, Any]
    synthesis: ResearchSynthesis
    trace: ExecutionTrace


def create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("get_bank_universe", _tool_get_bank_universe)
    registry.register("discover_bank_anomalies", _tool_discover_bank_anomalies)
    registry.register(
        "get_company_evidence",
        _tool_get_company_evidence,
        required_arguments={"ticker"},
    )
    registry.register(
        "compare_peer_metrics",
        _tool_compare_peer_metrics,
        required_arguments={"tickers"},
        allowed_arguments={"tickers", "metric"},
    )
    registry.register(
        "calculate_trends",
        _tool_calculate_trends,
        required_arguments={"ticker"},
    )
    return registry


def _tool_get_bank_universe(context: ToolExecutionContext) -> ToolOutput:
    if "universe_result" not in context.cache:
        context.cache["universe_result"] = context.provider.get_bank_universe()
    result = context.cache["universe_result"]
    return ToolOutput(
        value={
            "rows": result.universe.frame.to_dict(orient="records"),
            "pagination": result.universe.pagination,
        },
        evidence=(),
        status=result.status,
    )


def _tool_discover_bank_anomalies(context: ToolExecutionContext) -> ToolOutput:
    data = context.discovery_data()
    return ToolOutput(
        value={"anomalies": data.ranked.to_dict(orient="records")},
        evidence=tuple(data.evidence_ledger),
        status=data.status,
    )


def _tool_get_company_evidence(
    context: ToolExecutionContext,
    ticker: str,
) -> ToolOutput:
    company = context.cache.get(f"company:{ticker}")
    if company is None:
        company = context.provider.get_company_data(ticker)
        context.cache[f"company:{ticker}"] = company
    data = context.discovery_data()
    evidence = _evidence_for_tickers(data.evidence_ledger, [ticker])
    return ToolOutput(
        value={"company": company.data, "evidence_ids": [item.evidence_id for item in evidence]},
        evidence=evidence,
        status=company.status,
    )


def _tool_calculate_trends(context: ToolExecutionContext, ticker: str) -> ToolOutput:
    data = context.discovery_data()
    evidence = _evidence_for_tickers(data.evidence_ledger, [ticker])
    return ToolOutput(
        value={"trends": [item.to_dict() for item in evidence]},
        evidence=evidence,
        status=data.status,
    )


def _tool_compare_peer_metrics(
    context: ToolExecutionContext,
    tickers: list[str],
    metric: str | None = None,
) -> ToolOutput:
    if not isinstance(tickers, list) or len(tickers) < 1 or not all(
        isinstance(ticker, str) for ticker in tickers
    ):
        raise ValueError("tickers must be a non-empty list of ticker strings")
    if metric is not None and (not isinstance(metric, str) or not metric.strip()):
        raise ValueError("metric must be a non-empty string when supplied")
    data = context.discovery_data()
    evidence = _evidence_for_tickers(data.evidence_ledger, tickers)
    if metric is not None:
        evidence = tuple(item for item in evidence if item.metric.casefold() == metric.casefold())
    evidenced = {_ticker_key(item.ticker) for item in evidence}
    missing = [ticker for ticker in tickers if _ticker_key(ticker) not in evidenced]
    return ToolOutput(
        value={
            "tickers": tickers,
            "comparisons": [item.to_dict() for item in evidence],
            "tickers_without_evidence": missing,
            "metric": metric,
        },
        evidence=evidence,
        status=data.status,
    )


def _evidence_for_tickers(ledger: EvidenceLedger, tickers: list[str]) -> tuple[Evidence, ...]:
    requested = {_ticker_key(ticker) for ticker in tickers}
    return tuple(item for item in ledger if _ticker_key(item.ticker) in requested)


def _ticker_key(ticker: str) -> str:
    return ticker.strip().upper().removesuffix(".JK")


def _is_ticker(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"[A-Z0-9]{3,20}(?:\.JK)?", value, re.IGNORECASE)
    )


def _extract_tickers(request: str) -> tuple[str, ...]:
    tickers: list[str] = []
    seen: set[str] = set()
    for match in _TICKER_PATTERN.finditer(request.upper()):
        ticker = match.group(1).upper()
        if ticker in _TICKER_STOPWORDS:
            continue
        if len(ticker) == 4 and ticker.isalpha():
            ticker = f"{ticker}.JK"
        key = _ticker_key(ticker)
        if key not in seen:
            tickers.append(ticker)
            seen.add(key)
    return tuple(tickers)
