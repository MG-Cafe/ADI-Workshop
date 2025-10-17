from pathlib import Path

from backend.app.services.document_analyzer import DocumentAnalyzer


def test_fallback_parser_extracts_basic_fields():
    analyzer = DocumentAnalyzer()
    pdf_path = Path("DocumentProcessing_Invoices/DocumentProcessing_Invoices_Adatum/Train/Adatum 1.pdf")
    result = analyzer.analyze(pdf_path.read_bytes(), pdf_path.name)

    assert result.invoice_number == "1726"
    assert result.vendor_name and "ADATUM" in result.vendor_name.upper()
    assert result.subtotal == 147.29
    assert result.total_tax == 2.96
    assert result.total == 150.25
    assert len(result.line_items) == 3
