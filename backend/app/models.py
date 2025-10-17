from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlmodel import JSON, Column, Field, Relationship, SQLModel


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
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
    raw_fields: Dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    line_items: List["InvoiceLineItem"] = Relationship(back_populates="invoice")


class InvoiceLineItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None

    invoice: Invoice = Relationship(back_populates="line_items")
