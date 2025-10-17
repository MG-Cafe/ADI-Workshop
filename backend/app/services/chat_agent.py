from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from ..config import get_settings

try:  # pragma: no cover - optional dependency
    from openai import AzureOpenAI
except Exception:  # pragma: no cover - optional dependency
    AzureOpenAI = None  # type: ignore


@dataclass
class AgentContext:
    invoice_summary: Dict[str, Any]
    line_items: Iterable[Dict[str, Any]]


class ChatAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = self._build_client()

    def _build_client(self) -> Optional[AzureOpenAI]:  # type: ignore
        if (
            self.settings.azure_openai_endpoint
            and self.settings.azure_openai_api_key
            and self.settings.azure_openai_deployment
            and AzureOpenAI is not None
        ):
            return AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-02-15-preview",
            )
        return None

    def reply(self, prompt: str, context: AgentContext) -> str:
        if self._client is None:
            return self._fallback_response(prompt, context)
        return self._azure_response(prompt, context)

    def _azure_response(self, prompt: str, context: AgentContext) -> str:  # pragma: no cover - requires Azure
        system_prompt = (
            "You are an assistant that answers questions about invoices."
            " Use the provided JSON to reason about totals, dates, vendors,"
            " and line items. Respond concisely."
        )
        invoice_blob = json.dumps(
            {
                "invoice": context.invoice_summary,
                "line_items": list(context.line_items),
            },
            ensure_ascii=False,
        )
        response = self._client.responses.create(  # type: ignore[call-arg]
            model=self.settings.azure_openai_deployment,
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context: {invoice_blob}\n\nQuestion: {prompt}",
                },
            ],
        )
        output = response.output[0].content[0].text  # type: ignore[attr-defined]
        return output.strip()

    def _fallback_response(self, prompt: str, context: AgentContext) -> str:
        summary = context.invoice_summary
        prompt_lower = prompt.lower()
        if "total" in prompt_lower:
            total = summary.get("total")
            currency = summary.get("currency") or ""
            return f"The invoice total is {currency} {total}." if total else "I do not have a recorded total."
        if "due" in prompt_lower:
            due = summary.get("due_date")
            return f"The invoice is due on {due}." if due else "This invoice does not list a due date."
        if "vendor" in prompt_lower:
            vendor = summary.get("vendor_name")
            return f"The vendor is {vendor}." if vendor else "The vendor information is unavailable."
        if "items" in prompt_lower or "line" in prompt_lower:
            items = list(context.line_items)
            if not items:
                return "No line items were captured for this invoice."
            bullet_lines = [
                f"- {item.get('description', 'Unknown')} ({item.get('quantity', '?')} x {item.get('unit_price', '?')})"
                for item in items
            ]
            return "The invoice includes:\n" + "\n".join(bullet_lines)
        return "I can answer questions about totals, vendors, due dates, and line items when available."
