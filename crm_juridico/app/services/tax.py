"""Cálculo de IVA e IRPF al estilo declarando.es.

Reglas:
- IVA se aplica siempre sobre la base imponible.
- IRPF (retención) sólo cuando el destinatario es empresa/autónomo (B2B).
  Para particulares (B2C) la retención es 0.
- IRPF reducido (7%) durante los primeros 3 años de actividad si el cliente
  marca el flag irpf_nuevo.
"""
from dataclasses import dataclass


@dataclass
class InvoiceTotals:
    base_imponible: float
    tipo_iva: float
    importe_iva: float
    tipo_irpf: float
    importe_irpf: float
    total: float


def _round(value: float) -> float:
    return round(value + 1e-9, 2)


def applies_irpf(client_tipo: str) -> bool:
    return client_tipo in ("empresa", "autonomo")


def compute_totals(base_imponible: float, tipo_iva: float,
                   tipo_irpf: float) -> InvoiceTotals:
    base = _round(base_imponible)
    iva = _round(base * tipo_iva / 100.0)
    irpf = _round(base * tipo_irpf / 100.0)
    total = _round(base + iva - irpf)
    return InvoiceTotals(
        base_imponible=base,
        tipo_iva=tipo_iva,
        importe_iva=iva,
        tipo_irpf=tipo_irpf,
        importe_irpf=irpf,
        total=total,
    )


def line_subtotal(cantidad: float, precio_unitario: float) -> float:
    return _round(cantidad * precio_unitario)


def sum_lines(lines: list[dict]) -> float:
    return _round(sum(float(l.get("subtotal", 0)) for l in lines))
