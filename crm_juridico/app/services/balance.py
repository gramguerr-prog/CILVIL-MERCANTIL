"""Balance económico del despacho."""
from datetime import date

from app.database.db import fetch_all, fetch_one


def _period_clause(field: str, desde: str | None, hasta: str | None) -> tuple[str, list]:
    parts: list[str] = []
    params: list = []
    if desde:
        parts.append(f"{field} >= ?")
        params.append(desde)
    if hasta:
        parts.append(f"{field} <= ?")
        params.append(hasta)
    if not parts:
        return "", params
    return " AND " + " AND ".join(parts), params


def summary(desde: str | None = None, hasta: str | None = None) -> dict:
    inv_clause, inv_params = _period_clause("fecha_emision", desde, hasta)
    exp_clause, exp_params = _period_clause("fecha", desde, hasta)
    pay_clause, pay_params = _period_clause("fecha", desde, hasta)

    row = fetch_one(
        "SELECT COALESCE(SUM(base_imponible),0) AS base, "
        "COALESCE(SUM(importe_iva),0) AS iva, "
        "COALESCE(SUM(importe_irpf),0) AS irpf, "
        "COALESCE(SUM(total),0) AS total "
        "FROM invoices WHERE estado <> 'anulada'" + inv_clause,
        inv_params,
    )
    ingresos_base = float(row["base"])
    iva_repercutido = float(row["iva"])
    irpf_retenido = float(row["irpf"])
    total_facturado = float(row["total"])

    row = fetch_one(
        "SELECT COALESCE(SUM(base_imponible),0) AS base, "
        "COALESCE(SUM(importe_iva),0) AS iva, "
        "COALESCE(SUM(total),0) AS total "
        "FROM expenses WHERE deducible = 1" + exp_clause,
        exp_params,
    )
    gastos_base = float(row["base"])
    iva_soportado = float(row["iva"])
    total_gastos = float(row["total"])

    row = fetch_one(
        "SELECT COALESCE(SUM(importe),0) AS cobrado FROM payments WHERE 1=1" + pay_clause,
        pay_params,
    )
    cobrado = float(row["cobrado"])

    beneficio = ingresos_base - gastos_base
    iva_a_liquidar = iva_repercutido - iva_soportado
    pendiente_cobro = total_facturado - cobrado

    return {
        "ingresos_base": round(ingresos_base, 2),
        "iva_repercutido": round(iva_repercutido, 2),
        "irpf_retenido": round(irpf_retenido, 2),
        "total_facturado": round(total_facturado, 2),
        "gastos_base": round(gastos_base, 2),
        "iva_soportado": round(iva_soportado, 2),
        "total_gastos": round(total_gastos, 2),
        "beneficio": round(beneficio, 2),
        "iva_a_liquidar": round(iva_a_liquidar, 2),
        "cobrado": round(cobrado, 2),
        "pendiente_cobro": round(pendiente_cobro, 2),
    }


def top_clients(limit: int = 5, desde: str | None = None,
                hasta: str | None = None) -> list:
    clause, params = _period_clause("i.fecha_emision", desde, hasta)
    rows = fetch_all(
        "SELECT cl.id, cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente, "
        "COALESCE(SUM(i.total),0) AS total "
        "FROM invoices i JOIN clients cl ON cl.id = i.client_id "
        "WHERE i.estado <> 'anulada'" + clause +
        " GROUP BY cl.id ORDER BY total DESC LIMIT ?",
        params + [limit],
    )
    return [dict(r) for r in rows]


def monthly_series(year: int | None = None) -> list[dict]:
    year = year or date.today().year
    rows = fetch_all(
        "SELECT strftime('%m', fecha_emision) AS mes, "
        "COALESCE(SUM(base_imponible),0) AS ingresos "
        "FROM invoices WHERE estado <> 'anulada' "
        "AND strftime('%Y', fecha_emision) = ? "
        "GROUP BY mes ORDER BY mes",
        (str(year),),
    )
    ingresos_por_mes = {r["mes"]: float(r["ingresos"]) for r in rows}
    rows = fetch_all(
        "SELECT strftime('%m', fecha) AS mes, "
        "COALESCE(SUM(base_imponible),0) AS gastos "
        "FROM expenses WHERE deducible = 1 "
        "AND strftime('%Y', fecha) = ? "
        "GROUP BY mes ORDER BY mes",
        (str(year),),
    )
    gastos_por_mes = {r["mes"]: float(r["gastos"]) for r in rows}
    result = []
    for m in range(1, 13):
        clave = f"{m:02d}"
        result.append({
            "mes": clave,
            "ingresos": round(ingresos_por_mes.get(clave, 0), 2),
            "gastos": round(gastos_por_mes.get(clave, 0), 2),
        })
    return result
