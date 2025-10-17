from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..database import session_scope
from ..models import Invoice
from ..schemas import ChatMessage, ChatResponse
from ..services.chat_agent import AgentContext, ChatAgent

router = APIRouter()

chat_agent = ChatAgent()


@router.post("/{invoice_id}", response_model=ChatResponse)
def chat(invoice_id: int, payload: ChatMessage) -> ChatResponse:
    with session_scope() as session:
        invoice = session.exec(select(Invoice).where(Invoice.id == invoice_id)).one_or_none()
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        invoice.line_items  # load relationship

        context = AgentContext(
            invoice_summary={
                "invoice_number": invoice.invoice_number,
                "vendor_name": invoice.vendor_name,
                "customer_name": invoice.customer_name,
                "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "total": invoice.total,
                "currency": invoice.currency,
                "payment_terms": invoice.payment_terms,
            },
            line_items=[
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "amount": item.amount,
                }
                for item in invoice.line_items
            ],
        )

    response_text = chat_agent.reply(payload.message, context)
    return ChatResponse(response=response_text)
