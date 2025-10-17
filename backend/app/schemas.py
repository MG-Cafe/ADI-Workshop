from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = Field(default=None, alias="unitPrice")
    amount: Optional[float] = None

    class Config:
        allow_population_by_field_name = True


class InvoicePayload(BaseModel):
    id: int
    file_name: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_id: Optional[str] = None
    salesperson: Optional[str] = None
    payment_terms: Optional[str] = None
    subtotal: Optional[float] = None
    total_tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    raw_fields: Dict[str, Any]
    created_at: datetime
    line_items: List[LineItem] = []


class InvoiceCreateResponse(BaseModel):
    invoice: InvoicePayload
    message: str


class InvoiceListResponse(BaseModel):
    invoices: List[InvoicePayload]


class AnalyticsSummary(BaseModel):
    total_invoices: int
    total_value: float
    outstanding_balance: float
    vendors: Dict[str, float]
    currency: str = "USD"


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
