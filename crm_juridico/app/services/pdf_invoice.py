"""Generación de PDF de facturas con ReportLab."""

from __future__ import annotations
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from app.config import INVOICES_PDF_DIR
from app.database.db import get_setting


def _despacho_info() -> dict:
    return {
        "nombre": get_setting("despacho_nombre") or "",
        "nif": get_setting("despacho_nif") or "",
        "direccion": get_setting("despacho_direccion") or "",
        "telefono": get_setting("despacho_telefono") or "",
        "email": get_setting("despacho_email") or "",
        "iban": get_setting("despacho_iban") or "",
    }


def generate_invoice_pdf(invoice: dict, lines: list[dict],
                         out_dir: Path | None = None) -> Path:
    out_dir = out_dir or INVOICES_PDF_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_num = str(invoice["numero"]).replace("/", "-")
    out_path = out_dir / f"Factura_{safe_num}.pdf"

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18,
                        spaceAfter=6)
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=9, leading=11)

    despacho = _despacho_info()
    story = []
    story.append(Paragraph("FACTURA", h1))
    story.append(Paragraph(f"<b>Nº:</b> {invoice['numero']}", normal))
    story.append(Paragraph(f"<b>Fecha emisión:</b> {invoice['fecha_emision']}", normal))
    if invoice.get("fecha_vencimiento"):
        story.append(Paragraph(f"<b>Vencimiento:</b> {invoice['fecha_vencimiento']}", normal))
    story.append(Spacer(1, 8))

    emisor_html = (
        f"<b>{despacho['nombre']}</b><br/>"
        f"NIF: {despacho['nif']}<br/>"
        f"{despacho['direccion']}<br/>"
        f"Tel: {despacho['telefono']} · {despacho['email']}"
    )
    cliente_html = (
        f"<b>{invoice.get('cliente_nombre','')}</b><br/>"
        f"NIF: {invoice.get('cliente_nif','') or ''}<br/>"
        f"{invoice.get('cliente_direccion','') or ''}<br/>"
        f"{invoice.get('cliente_email','') or ''}"
    )
    header_table = Table(
        [[Paragraph("EMISOR", small), Paragraph("CLIENTE", small)],
         [Paragraph(emisor_html, small), Paragraph(cliente_html, small)]],
        colWidths=[85 * mm, 85 * mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    data = [["Descripción", "Cant.", "Precio", "Subtotal"]]
    for ln in lines:
        data.append([
            Paragraph(str(ln.get("descripcion", "")), small),
            f"{float(ln.get('cantidad', 0)):.2f}",
            f"{float(ln.get('precio_unitario', 0)):.2f} €",
            f"{float(ln.get('subtotal', 0)):.2f} €",
        ])
    lines_table = Table(
        data, colWidths=[95 * mm, 20 * mm, 25 * mm, 30 * mm],
    )
    lines_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(lines_table)
    story.append(Spacer(1, 10))

    base = float(invoice["base_imponible"])
    iva = float(invoice["importe_iva"])
    irpf = float(invoice["importe_irpf"])
    total = float(invoice["total"])
    tot_data = [
        ["Base imponible", f"{base:.2f} €"],
        [f"IVA ({invoice['tipo_iva']:.0f} %)", f"{iva:.2f} €"],
    ]
    if irpf > 0:
        tot_data.append([f"Retención IRPF ({invoice['tipo_irpf']:.0f} %)", f"-{irpf:.2f} €"])
    tot_data.append(["TOTAL", f"{total:.2f} €"])

    tot_table = Table(tot_data, colWidths=[60 * mm, 30 * mm], hAlign="RIGHT")
    tot_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tot_table)
    story.append(Spacer(1, 14))

    if despacho["iban"]:
        story.append(Paragraph(
            f"<b>Forma de pago:</b> transferencia bancaria a IBAN "
            f"<font face='Helvetica-Bold'>{despacho['iban']}</font>", small,
        ))
    if invoice.get("notas"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Notas:</b> {invoice['notas']}", small))

    doc.build(story)
    return out_path
