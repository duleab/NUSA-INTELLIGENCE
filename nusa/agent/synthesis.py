"""Evidence-constrained LLM synthesis with an offline deterministic fallback."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlsplit

from nusa.discovery.evidence import Evidence, EvidenceLedger


_OUTPUT_FIELDS = (
    "executive_summary",
    "key_findings",
    "historical_context",
    "peer_comparison",
    "why_flagged",
    "limitations",
    "evidence_references",
)
_LIST_FIELDS = _OUTPUT_FIELDS[1:]
_SYSTEM_PROMPT = """You are NUSA Intelligence's research-writing component. Use ONLY the supplied, validated evidence for financial facts. Never invent missing values or calculate/derive financial numbers; deterministic analytics already did that. Explicitly state data limitations. Do not issue BUY or SELL recommendations or personalized investment advice. An anomaly is a research-priority signal, not evidence of misconduct or fraud; explicitly distinguish these. Cite supplied evidence IDs where appropriate. Do not reveal hidden reasoning or provide chain-of-thought. Return one JSON object with exactly these fields: executive_summary (string), key_findings (array of strings), historical_context (array of strings), peer_comparison (array of strings), why_flagged (array of strings), limitations (array of strings), evidence_references (array of supplied evidence ID strings)."""
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![A-Za-z0-9_])")


class LLMProvider(Protocol):
    """Minimal injectable JSON completion interface."""

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return a parsed JSON object, or raise a provider error."""


class OpenAICompatibleLLMProvider:
    """Small OpenAI-compatible chat-completions client using stdlib HTTP."""

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout: float = 30.0) -> None:
        if not api_key.strip() or not model.strip():
            raise ValueError("LLM API key and model are required")
        parsed_url = urlsplit(base_url)
        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("LLM base URL must use HTTPS")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = self.base_url if self.base_url.endswith("/chat/completions") else (
            self.base_url + "/chat/completions"
        )
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
            # Deliberately omit exception text: HTTP/library errors may contain URLs or headers.
            raise RuntimeError("LLM provider request failed") from None
        try:
            content = body["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError):
            raise RuntimeError("LLM provider returned an invalid JSON response") from None
        if not isinstance(result, dict):
            raise RuntimeError("LLM provider returned an invalid JSON object")
        return result


def create_llm_provider_from_env(environ: dict[str, str] | None = None) -> LLMProvider | None:
    """Create configured provider; missing key means offline template mode."""
    env = os.environ if environ is None else environ
    api_key = env.get("NUSA_LLM_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = env.get("NUSA_LLM_BASE_URL", "").strip()
    model = env.get("NUSA_LLM_MODEL", "").strip()
    provider_name = env.get("NUSA_LLM_PROVIDER", "openai_compatible").strip().casefold()
    if provider_name != "openai_compatible":
        raise ValueError("Unsupported LLM provider; supported provider: openai_compatible")
    if not base_url or not model:
        raise ValueError("NUSA_LLM_BASE_URL and NUSA_LLM_MODEL are required when an API key is set")
    return OpenAICompatibleLLMProvider(api_key=api_key, base_url=base_url, model=model)


@dataclass(frozen=True)
class ResearchSynthesis:
    executive_summary: str
    key_findings: list[str]
    historical_context: list[str]
    peer_comparison: list[str]
    why_flagged: list[str]
    limitations: list[str]
    evidence_references: list[str]
    generation_mode: str = "template"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LLMResearchSynthesizer:
    """Synthesize only validated ledger entries; fail closed to sourced templates."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def synthesize(
        self,
        request: str,
        plan: dict[str, Any],
        evidence: EvidenceLedger,
        *,
        data_source: dict[str, Any] | None = None,
    ) -> ResearchSynthesis:
        if self.provider is None:
            return self._template(evidence, data_source=data_source)
        payload = {
            "request": request,
            "plan": plan,
            "data_source": data_source or {},
            "validated_evidence": evidence.to_llm_context()["evidence"],
        }
        try:
            raw = self.provider.complete_json(_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False))
            result = _parse_synthesis(raw)
            _validate_references(result, evidence)
            _validate_numeric_claims(result, evidence)
            return ResearchSynthesis(**{**result, "generation_mode": "llm"})
        except Exception as exc:
            reason = "LLM synthesis was unavailable or failed safety validation; deterministic evidence summary shown."
            if "unsupported numeric" in str(exc).lower():
                reason = "LLM synthesis included an unsupported numeric claim; deterministic evidence summary shown."
            return self._template(evidence, data_source=data_source, extra_limitations=[reason])

    def answer_followup(
        self,
        question: str,
        evidence: EvidenceLedger,
        previous: ResearchSynthesis | None,
        *,
        data_source: dict[str, Any] | None = None,
    ) -> ResearchSynthesis:
        if not question.strip():
            raise ValueError("Follow-up question must not be empty")
        if self.provider is None:
            result = self._template(evidence, data_source=data_source)
            return ResearchSynthesis(
                executive_summary=(
                    "A contextual answer requires the configured LLM provider; "
                    "the validated evidence summary is provided instead. " + result.executive_summary
                ),
                key_findings=result.key_findings,
                historical_context=result.historical_context,
                peer_comparison=result.peer_comparison,
                why_flagged=result.why_flagged,
                limitations=result.limitations,
                evidence_references=result.evidence_references,
                generation_mode="template",
            )
        payload = {
            "follow_up_question": question,
            "prior_synthesis": None if previous is None else previous.to_dict(),
            "data_source": data_source or {},
            "validated_evidence": evidence.to_llm_context()["evidence"],
        }
        try:
            model_result = _parse_synthesis(
                self.provider.complete_json(_SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False))
            )
            _validate_references(model_result, evidence)
            _validate_numeric_claims(model_result, evidence)
            return ResearchSynthesis(**{**model_result, "generation_mode": "llm"})
        except Exception:
            return self._template(
                evidence,
                data_source=data_source,
                extra_limitations=["Follow-up synthesis failed safety validation; deterministic evidence summary shown."],
            )

    def plan_from_request(self, request: str, registry: Any):
        """Ask for a plan only after deterministic parsing fails; validate it against allowlist."""
        if self.provider is None:
            raise ValueError("No LLM provider is configured")
        system = (
            "Map the user request to exactly one intent: DISCOVER, INVESTIGATE, COMPARE. "
            "Return JSON with fields intent, tickers (array of IDX bank ticker strings), "
            "tasks (array of objects with tool, purpose, arguments). Use only these tools: "
            + ", ".join(sorted(registry.names()))
            + ". Do not invent tickers or add tools. No prose."
        )
        raw = self.provider.complete_json(system, json.dumps({"request": request}))
        try:
            from nusa.agent.orchestration import (
                PlanValidationError,
                ResearchPlan,
                ResearchTask,
                ResolvedIntent,
                _extract_tickers,
                validate_plan,
            )

            intent = raw["intent"]
            tickers = tuple(str(item).upper() for item in raw["tickers"])
            tasks = [
                ResearchTask(item["tool"], item["purpose"], item.get("arguments", {}))
                for item in raw["tasks"]
            ]
            resolved = ResolvedIntent(intent, tickers)
            plan = ResearchPlan(request.strip(), intent, tickers[0] if tickers else None, tasks, tickers)
            # A model may classify wording, but the ticker identity must come from the request.
            mentioned = set(_extract_tickers(request))
            if set(tickers) != mentioned:
                raise PlanValidationError("Model plan tickers do not match the request")
            validate_plan(plan, registry)
            return resolved, plan
        except Exception:
            raise ValueError("LLM could not produce a safe, supported research plan") from None

    @staticmethod
    def _template(
        evidence: EvidenceLedger,
        *,
        data_source: dict[str, Any] | None = None,
        extra_limitations: list[str] | None = None,
    ) -> ResearchSynthesis:
        items = list(evidence)
        refs = [item.evidence_id for item in items]
        limitations = [
            "Findings are limited to the validated evidence supplied by the data provider.",
            "An anomaly is a research-priority signal, not evidence of misconduct or fraud.",
            "This is not a BUY/SELL recommendation or personalized investment advice.",
        ]
        if not items:
            limitations.insert(0, "No validated quantitative evidence is available for this request.")
        source_warning = (data_source or {}).get("warning")
        if source_warning:
            limitations.append(str(source_warning))
        limitations.extend(extra_limitations or [])
        findings = [_evidence_line(item) for item in items]
        if not findings:
            summary = "No validated financial evidence is available to support a quantitative conclusion."
        else:
            summary = (
                f"Reviewed {len(items)} validated metric record(s). First finding: {findings[0]}"
            )
        return ResearchSynthesis(
            executive_summary=summary,
            key_findings=findings,
            historical_context=[
                f"{item.ticker} {item.metric}: {item.period}; "
                f"previous={_fmt(item.previous_value)}, current={_fmt(item.current_value)} [{item.evidence_id}]"
                for item in items
            ],
            peer_comparison=[
                f"{item.ticker} {item.metric}: peer median change={_fmt(item.peer_median)}, "
                f"peer count={_fmt(item.peer_count)} [{item.evidence_id}]"
                for item in items if item.peer_median is not None or item.peer_count is not None
            ],
            why_flagged=[
                f"{item.ticker} {item.metric}: observed change={_fmt(item.change)}; "
                f"deviation={_fmt(item.deviation)} [{item.evidence_id}]"
                for item in items if item.change is not None or item.deviation is not None
            ],
            limitations=limitations,
            evidence_references=refs,
        )


def _parse_synthesis(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != set(_OUTPUT_FIELDS):
        raise ValueError("synthesis response schema mismatch")
    if not isinstance(raw["executive_summary"], str) or not raw["executive_summary"].strip():
        raise ValueError("executive summary must be a non-empty string")
    result: dict[str, Any] = {"executive_summary": raw["executive_summary"].strip()}
    for field in _LIST_FIELDS:
        value = raw[field]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field} must be an array of strings")
        result[field] = [item.strip() for item in value if item.strip()]
    return result


def _validate_references(result: dict[str, Any], evidence: EvidenceLedger) -> None:
    allowed = {item.evidence_id for item in evidence}
    references = result["evidence_references"]
    if any(reference not in allowed for reference in references):
        raise ValueError("unknown evidence reference")
    if allowed and not references:
        raise ValueError("evidence references are required")


def _validate_numeric_claims(result: dict[str, Any], evidence: EvidenceLedger) -> None:
    allowed: set[Decimal] = set()
    for item in evidence:
        for name in ("current_value", "previous_value", "change", "peer_median", "peer_count", "deviation"):
            value = getattr(item, name)
            if value is not None:
                allowed.add(Decimal(str(value)))
        for year in re.findall(r"\d{4}", item.period):
            allowed.add(Decimal(year))
    for text in [result["executive_summary"]] + [
        line for field in _LIST_FIELDS for line in result[field]
    ]:
        scrubbed = re.sub(r"\[?[^\]\s]*evidence[^\]\s]*\]?", "", text, flags=re.I)
        scrubbed = re.sub(r"\[?ev-[A-Za-z0-9_-]+\]?", "", scrubbed, flags=re.I)
        for token in _NUMBER_RE.findall(scrubbed):
            try:
                number = Decimal(token.replace(",", "").rstrip("%"))
            except InvalidOperation:
                continue
            if number not in allowed:
                raise ValueError("unsupported numeric claim")


def _evidence_line(item: Evidence) -> str:
    company = f" ({item.company_name})" if item.company_name else ""
    return (
        f"{item.ticker}{company} {item.metric}, {item.period}: "
        f"previous={_fmt(item.previous_value)}, current={_fmt(item.current_value)}, "
        f"change={_fmt(item.change)}, peer median={_fmt(item.peer_median)}, "
        f"deviation={_fmt(item.deviation)} [{item.evidence_id}]"
    )


def _fmt(value: Any) -> str:
    return "not available" if value is None else str(value)
