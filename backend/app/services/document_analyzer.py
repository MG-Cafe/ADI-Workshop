from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import get_settings

LOGGER = logging.getLogger(__name__)

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import (
        AnalyzeDocumentFeature,
        AnalyzeDocumentRequest,
    )
    from azure.core.credentials import AzureKeyCredential
except Exception:  # pragma: no cover - optional dependency
    DocumentIntelligenceClient = None  # type: ignore
    AzureKeyCredential = None  # type: ignore
    AnalyzeDocumentRequest = None  # type: ignore
    AnalyzeDocumentFeature = None  # type: ignore


@dataclass
class AnalyzedLineItem:
    description: Optional[str]
    quantity: Optional[float]
    unit_price: Optional[float]
    amount: Optional[float]


@dataclass
class AnalyzedInvoice:
    invoice_number: Optional[str]
    vendor_name: Optional[str]
    vendor_address: Optional[str]
    invoice_date: Optional[datetime]
    due_date: Optional[datetime]
    customer_name: Optional[str]
    customer_address: Optional[str]
    customer_id: Optional[str]
    salesperson: Optional[str]
    payment_terms: Optional[str]
    subtotal: Optional[float]
    total_tax: Optional[float]
    total: Optional[float]
    currency: Optional[str]
    line_items: List[AnalyzedLineItem]
    raw_fields: Dict[str, Any]


class AnalyzerError(RuntimeError):
    """Raised when the document analyzer fails."""


class DocumentAnalyzer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = self._build_client()

    def _build_client(self) -> Optional[DocumentIntelligenceClient]:  # type: ignore
        if (
            self.settings.azure_document_intelligence_endpoint
            and self.settings.azure_document_intelligence_key
            and DocumentIntelligenceClient is not None
        ):
            credential = AzureKeyCredential(self.settings.azure_document_intelligence_key)
            return DocumentIntelligenceClient(
                endpoint=self.settings.azure_document_intelligence_endpoint,
                credential=credential,
            )
        LOGGER.warning(
            "Azure Document Intelligence credentials not configured; falling back to local parser."
        )
        return None

    def analyze(self, file_bytes: bytes, file_name: str) -> AnalyzedInvoice:
        if self._client is not None:
            try:
                return self._analyze_with_service(file_bytes)
            except Exception as exc:  # pragma: no cover - service failure path
                LOGGER.exception("Azure Document Intelligence failed; attempting fallback parser")
                raise AnalyzerError(str(exc))
        return self._analyze_with_fallback(file_bytes, file_name)

    # Azure service -----------------------------------------------------
    def _analyze_with_service(self, file_bytes: bytes) -> AnalyzedInvoice:  # pragma: no cover - requires Azure
        assert self._client is not None
        assert AnalyzeDocumentRequest is not None
        assert AnalyzeDocumentFeature is not None

        request = AnalyzeDocumentRequest(bytes_source=file_bytes)
        poller = self._client.begin_analyze_document(
            model_id="prebuilt-invoice",
            analyze_request=request,
            features=[AnalyzeDocumentFeature.KEY_VALUE_PAIRS, AnalyzeDocumentFeature.TABLES],
        )
        result = poller.result()
        if not result.documents:
            raise AnalyzerError("Document analysis returned no documents")

        document = result.documents[0]
        fields = document.fields or {}

        def _field_value(name: str) -> Optional[Any]:
            field = fields.get(name)
            if field is None:
                return None
            return getattr(field, "value", None) or getattr(field, "content", None)

        line_items: List[AnalyzedLineItem] = []
        items_field = fields.get("Items")
        if items_field and items_field.value:
            for item in items_field.value:
                if not getattr(item, "value", None):
                    continue
                value = item.value
                line_items.append(
                    AnalyzedLineItem(
                        description=self._safe_field(value, "Description"),
                        quantity=self._safe_float(value, "Quantity"),
                        unit_price=self._safe_float(value, "UnitPrice"),
                        amount=self._safe_float(value, "Amount"),
                    )
                )

        def _parse_date(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(str(value))
            except Exception:
                return None

        raw_fields = {name: self._normalize_field(value) for name, value in fields.items()}

        return AnalyzedInvoice(
            invoice_number=_field_value("InvoiceId") or _field_value("InvoiceNumber"),
            vendor_name=_field_value("VendorName"),
            vendor_address=_field_value("VendorAddress"),
            invoice_date=_parse_date(_field_value("InvoiceDate")),
            due_date=_parse_date(_field_value("DueDate")),
            customer_name=_field_value("CustomerName"),
            customer_address=_field_value("CustomerAddress"),
            customer_id=_field_value("CustomerId"),
            salesperson=_field_value("SalesPerson"),
            payment_terms=_field_value("PaymentTerms"),
            subtotal=self._safe_float(fields, "SubTotal"),
            total_tax=self._safe_float(fields, "TotalTax"),
            total=self._safe_float(fields, "InvoiceTotal"),
            currency=_field_value("Currency"),
            line_items=line_items,
            raw_fields=raw_fields,
        )

    @staticmethod
    def _safe_field(container: Dict[str, Any], key: str) -> Optional[str]:
        field = container.get(key)
        if field is None:
            return None
        return getattr(field, "value", None) or getattr(field, "content", None)

    @staticmethod
    def _safe_float(container: Dict[str, Any], key: str) -> Optional[float]:
        field = container.get(key)
        if field is None:
            return None
        value = getattr(field, "value", None) or getattr(field, "content", None)
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _normalize_field(field: Any) -> Any:
        if hasattr(field, "value"):
            return field.value
        if hasattr(field, "content"):
            return field.content
        return field

    # Fallback parser ---------------------------------------------------
    def _analyze_with_fallback(self, file_bytes: bytes, file_name: str) -> AnalyzedInvoice:
        try:
            text = self._extract_text(file_bytes)
        except Exception as exc:  # pragma: no cover - binary parsing failure
            raise AnalyzerError(f"Unable to extract text from {file_name}: {exc}") from exc

        normalized = re.sub(r" +", " ", text)
        normalized = re.sub(r"\s+", " ", normalized)

        def match(pattern: str) -> Optional[str]:
            found = re.search(pattern, normalized)
            return found.group(1).strip() if found else None

        def parse_money(value: Optional[str]) -> Optional[float]:
            if not value:
                return None
            try:
                return float(value.replace(",", ""))
            except ValueError:
                return None

        invoice_number = match(r"INVOICE NO\s+([A-Za-z0-9-]+)")
        invoice_date_text = match(r"DATE\s+([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})")
        invoice_date = None
        if invoice_date_text:
            for fmt in ("%b %d, %Y", "%B %d, %Y"):
                try:
                    invoice_date = datetime.strptime(invoice_date_text, fmt)
                    break
                except ValueError:
                    continue

        vendor_block = match(r"INVOICE NO\s+[A-Za-z0-9-]+\s+(.*?)INVOICE TO")
        customer_block = match(r"INVOICE TO\s+(.*?)SALESPERSON")
        salesperson = match(r"SALESPERSON\s+([A-Za-z ]+)")
        payment_terms = match(r"PAYMENT TERMS\s+([A-Za-z ]+)")
        customer_id = match(r"Customer Id:\s*([A-Za-z0-9-]+)")

        subtotal = parse_money(match(r"Subtotal:\s*\$([0-9.,]+)"))
        total_tax = parse_money(match(r"Sales Tax:\s*\$([0-9.,]+)"))
        total = parse_money(match(r"Total:\s*\$([0-9.,]+)"))

        line_items: List[AnalyzedLineItem] = []
        items_match = re.search(
            r"QUANTITY DESCRIPTION UNIT PRICE LINE TOTAL (.*?)Subtotal:", normalized
        )
        if items_match:
            section = items_match.group(1)
            for qty, desc, unit_price, amount in re.findall(
                r"(\d{1,3})\s+([A-Za-z0-9 ,./-]+?)\s+\$([0-9.,]+)\s+\$([0-9.,]+)",
                section,
            ):
                line_items.append(
                    AnalyzedLineItem(
                        description=desc.strip(),
                        quantity=float(qty),
                        unit_price=parse_money(unit_price),
                        amount=parse_money(amount),
                    )
                )

        raw_fields: Dict[str, Any] = {
            "text": normalized,
        }

        return AnalyzedInvoice(
            invoice_number=invoice_number,
            vendor_name=self._first_line(vendor_block),
            vendor_address=vendor_block,
            invoice_date=invoice_date,
            due_date=None,
            customer_name=self._first_line(customer_block),
            customer_address=customer_block,
            customer_id=customer_id,
            salesperson=salesperson,
            payment_terms=payment_terms,
            subtotal=subtotal,
            total_tax=total_tax,
            total=total,
            currency="USD" if total is not None else None,
            line_items=line_items,
            raw_fields=raw_fields,
        )

    @staticmethod
    def _extract_text(file_bytes: bytes) -> str:
        import zlib

        text_parts: List[str] = []
        for match in re.finditer(b"stream\r?\n", file_bytes):
            start = match.end()
            end = file_bytes.find(b"endstream", start)
            if end == -1:
                continue
            stream = file_bytes[start:end]
            try:
                decoded = zlib.decompress(stream.strip())
            except Exception:
                continue
            for item in re.findall(rb"\(([^()]*)\)", decoded):
                token = item.decode("latin1", errors="ignore")
                if token:
                    text_parts.append(token)
        return "".join(text_parts)

    @staticmethod
    def _first_line(block: Optional[str]) -> Optional[str]:
        if not block:
            return None
        clean = block.strip()
        for marker in (" www", " http", " Customer", " SALESPERSON", " Subtotal"):
            index = clean.find(marker)
            if index != -1:
                clean = clean[:index]
                break
        clean = clean.strip()
        match = re.search(r"([A-Za-z][A-Za-z &.,'-]+)", clean)
        if match:
            return match.group(1).strip()
        return clean
