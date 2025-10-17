from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable

from ..models import Invoice


def aggregate(invoices: Iterable[Invoice]) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for invoice in invoices:
        vendor = invoice.vendor_name or "Unknown"
        if invoice.total:
            totals[vendor] += invoice.total
    return dict(totals)
