from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from ..database import session_scope
from ..models import Invoice, InvoiceLineItem
from ..schemas import (
    AnalyticsSummary,
    InvoiceCreateResponse,
    InvoiceListResponse,
    InvoicePayload,
    LineItem,
)
from ..services.analytics import aggregate
from ..services.document_analyzer import AnalyzerError, DocumentAnalyzer

router = APIRouter()

document_analyzer = DocumentAnalyzer()


def _to_payload(invoice: Invoice) -> InvoicePayload:
    return InvoicePayload(
        id=invoice.id,
        file_name=invoice.file_name,
        invoice_number=invoice.invoice_number,
        vendor_name=invoice.vendor_name,
        vendor_address=invoice.vendor_address,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        customer_name=invoice.customer_name,
        customer_address=invoice.customer_address,
        customer_id=invoice.customer_id,
        salesperson=invoice.salesperson,
        payment_terms=invoice.payment_terms,
        subtotal=invoice.subtotal,
        total_tax=invoice.total_tax,
        total=invoice.total,
        currency=invoice.currency,
        raw_fields=invoice.raw_fields,
        created_at=invoice.created_at,
        line_items=[
            LineItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.amount,
            )
            for item in invoice.line_items
        ],
    )


@router.post("/", response_model=InvoiceCreateResponse)
async def create_invoice(file: UploadFile = File(...)) -> InvoiceCreateResponse:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        analysis = document_analyzer.analyze(file_bytes, file.filename)
    except AnalyzerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    invoice_record = Invoice(
        file_name=file.filename,
        invoice_number=analysis.invoice_number,
        vendor_name=analysis.vendor_name,
        vendor_address=analysis.vendor_address,
        invoice_date=analysis.invoice_date.date() if isinstance(analysis.invoice_date, datetime) else analysis.invoice_date,
        due_date=analysis.due_date.date() if isinstance(analysis.due_date, datetime) else analysis.due_date,
        customer_name=analysis.customer_name,
        customer_address=analysis.customer_address,
        customer_id=analysis.customer_id,
        salesperson=analysis.salesperson,
        payment_terms=analysis.payment_terms,
        subtotal=analysis.subtotal,
        total_tax=analysis.total_tax,
        total=analysis.total,
        currency=analysis.currency,
        raw_fields=analysis.raw_fields,
    )

    with session_scope() as session:
        try:
            session.add(invoice_record)
            session.commit()
            session.refresh(invoice_record)
            for item in analysis.line_items:
                session.add(
                    InvoiceLineItem(
                        invoice_id=invoice_record.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        amount=item.amount,
                    )
                )
            session.commit()
            session.refresh(invoice_record)
        except SQLAlchemyError as exc:  # pragma: no cover - database failure
            session.rollback()
            raise HTTPException(status_code=500, detail="Database error while saving invoice") from exc

        invoice_with_items = session.exec(
            select(Invoice).where(Invoice.id == invoice_record.id)
        ).one()
        payload = _to_payload(invoice_with_items)
        return InvoiceCreateResponse(
            invoice=payload,
            message="Invoice processed successfully",
        )


@router.get("/", response_model=InvoiceListResponse)
def list_invoices() -> InvoiceListResponse:
    with session_scope() as session:
        invoices = session.exec(select(Invoice).order_by(Invoice.created_at.desc())).all()
        for invoice in invoices:
            invoice.line_items  # load relationship
        return InvoiceListResponse(invoices=[_to_payload(invoice) for invoice in invoices])


@router.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary() -> AnalyticsSummary:
    with session_scope() as session:
        invoices = session.exec(select(Invoice)).all()
        vendor_totals = aggregate(invoices)
        total_value = sum(invoice.total or 0 for invoice in invoices)
        outstanding = sum(invoice.total or 0 for invoice in invoices if invoice.due_date)
        return AnalyticsSummary(
            total_invoices=len(invoices),
            total_value=total_value,
            outstanding_balance=outstanding,
            vendors=vendor_totals,
        )


@router.get("/{invoice_id}", response_model=InvoicePayload)
def get_invoice(invoice_id: int) -> InvoicePayload:
    with session_scope() as session:
        invoice = session.exec(select(Invoice).where(Invoice.id == invoice_id)).one_or_none()
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        invoice.line_items  # load relationship
        return _to_payload(invoice)
