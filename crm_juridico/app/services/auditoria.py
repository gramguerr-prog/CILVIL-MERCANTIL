"""Auditoría de los datos del despacho.

La detección se hace con reglas deterministas en código, no preguntándole a la
IA: un hueco en la numeración de facturas o una retención mal aplicada son
hechos comprobables, y una respuesta probabilística no vale aquí. La IA se usa
después, solo para explicar y priorizar lo que estas reglas encuentran.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta

from app.database.db import fetch_all
from app.services.tax import applies_irpf

SEVERIDADES = ("alta", "media", "baja")

# Meses sin anotaciones a partir de los cuales un asunto abierto se marca.
MESES_INACTIVIDAD = 6
# Margen de redondeo admitido al recalcular los totales de una factura.
TOLERANCIA_EUR = 0.02


@dataclass
class Hallazgo:
    codigo: str
    severidad: str
    titulo: str
    detalle: str
    entidad: str = ""
    client_id: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _hoy() -> date:
    return date.today()


# ---------------------------------------------------------------- facturación

def _facturas_vencidas() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT i.numero, i.fecha_vencimiento, i.total, i.client_id, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente "
        "FROM invoices i JOIN clients cl ON cl.id = i.client_id "
        "WHERE i.estado IN ('emitida','parcial') "
        "AND i.fecha_vencimiento IS NOT NULL AND i.fecha_vencimiento <> '' "
        "AND i.fecha_vencimiento < ? ORDER BY i.fecha_vencimiento",
        (_hoy().isoformat(),),
    )
    hallazgos = []
    for f in filas:
        dias = (_hoy() - date.fromisoformat(f["fecha_vencimiento"])).days
        hallazgos.append(Hallazgo(
            codigo="factura_vencida",
            severidad="alta" if dias > 90 else "media",
            titulo=f"Factura {f['numero']} vencida hace {dias} días",
            detalle=(f"{float(f['total']):.2f} € pendientes de {f['cliente'].strip()}. "
                     f"Venció el {f['fecha_vencimiento']}."),
            entidad=f["numero"],
            client_id=f["client_id"],
        ))
    return hallazgos


def _huecos_numeracion() -> list[Hallazgo]:
    """La numeración de facturas debe ser correlativa y sin saltos."""
    filas = fetch_all(
        "SELECT serie, correlativo, numero FROM invoices "
        "WHERE estado <> 'borrador' ORDER BY serie, correlativo"
    )
    por_serie: dict[str, list[int]] = {}
    for f in filas:
        por_serie.setdefault(f["serie"], []).append(int(f["correlativo"]))

    hallazgos = []
    for serie, correlativos in por_serie.items():
        vistos = sorted(set(correlativos))
        if not vistos:
            continue
        faltan = [n for n in range(vistos[0], vistos[-1] + 1) if n not in vistos]
        if faltan:
            listado = ", ".join(str(n) for n in faltan[:15])
            if len(faltan) > 15:
                listado += f" … (+{len(faltan) - 15} más)"
            hallazgos.append(Hallazgo(
                codigo="numeracion_con_huecos",
                severidad="alta",
                titulo=f"Faltan números correlativos en la serie {serie}",
                detalle=(f"No existen las facturas nº {listado}. La numeración "
                         "debe ser correlativa y sin saltos; si anulaste alguna, "
                         "debe constar con estado «anulada», no desaparecer."),
                entidad=f"serie {serie}",
            ))
        duplicados = {n for n in correlativos if correlativos.count(n) > 1}
        if duplicados:
            hallazgos.append(Hallazgo(
                codigo="numeracion_duplicada",
                severidad="alta",
                titulo=f"Números repetidos en la serie {serie}",
                detalle=("Aparecen dos o más facturas con el correlativo "
                         + ", ".join(str(n) for n in sorted(duplicados)) + "."),
                entidad=f"serie {serie}",
            ))
    return hallazgos


def _irpf_incoherente() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT i.numero, i.tipo_irpf, i.client_id, cl.tipo AS tipo_cliente, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente "
        "FROM invoices i JOIN clients cl ON cl.id = i.client_id "
        "WHERE i.estado <> 'anulada'"
    )
    hallazgos = []
    for f in filas:
        debe_retener = applies_irpf(f["tipo_cliente"] or "particular")
        tiene_retencion = float(f["tipo_irpf"] or 0) > 0
        if debe_retener and not tiene_retencion:
            hallazgos.append(Hallazgo(
                codigo="irpf_faltante",
                severidad="alta",
                titulo=f"Factura {f['numero']} sin retención de IRPF",
                detalle=(f"{f['cliente'].strip()} está dado de alta como "
                         f"«{f['tipo_cliente']}», así que la factura debería "
                         "llevar retención. Revisa si procede rectificarla."),
                entidad=f["numero"],
                client_id=f["client_id"],
            ))
        elif not debe_retener and tiene_retencion:
            hallazgos.append(Hallazgo(
                codigo="irpf_indebido",
                severidad="alta",
                titulo=f"Factura {f['numero']} con retención sobre un particular",
                detalle=(f"{f['cliente'].strip()} figura como «{f['tipo_cliente']}». "
                         "A particulares no se les practica retención de IRPF."),
                entidad=f["numero"],
                client_id=f["client_id"],
            ))
    return hallazgos


def _totales_descuadrados() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT numero, base_imponible, tipo_iva, importe_iva, tipo_irpf, "
        "importe_irpf, total, client_id FROM invoices WHERE estado <> 'anulada'"
    )
    hallazgos = []
    for f in filas:
        base = float(f["base_imponible"] or 0)
        iva_esperado = round(base * float(f["tipo_iva"] or 0) / 100, 2)
        irpf_esperado = round(base * float(f["tipo_irpf"] or 0) / 100, 2)
        total_esperado = round(base + iva_esperado - irpf_esperado, 2)
        if abs(total_esperado - float(f["total"] or 0)) > TOLERANCIA_EUR:
            hallazgos.append(Hallazgo(
                codigo="total_descuadrado",
                severidad="alta",
                titulo=f"Los importes de la factura {f['numero']} no cuadran",
                detalle=(f"Base {base:.2f} € + IVA {iva_esperado:.2f} € − IRPF "
                         f"{irpf_esperado:.2f} € = {total_esperado:.2f} €, pero "
                         f"la factura dice {float(f['total'] or 0):.2f} €. "
                         "Ábrela y vuelve a guardarla para recalcularla."),
                entidad=f["numero"],
                client_id=f["client_id"],
            ))
    return hallazgos


def _facturas_sin_lineas() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT i.numero, i.client_id FROM invoices i "
        "LEFT JOIN invoice_lines l ON l.invoice_id = i.id "
        "WHERE i.estado <> 'anulada' GROUP BY i.id HAVING COUNT(l.id) = 0"
    )
    return [Hallazgo(
        codigo="factura_sin_lineas",
        severidad="media",
        titulo=f"La factura {f['numero']} no tiene ningún concepto",
        detalle="Una factura sin desglose no cumple los requisitos de contenido.",
        entidad=f["numero"],
        client_id=f["client_id"],
    ) for f in filas]


def _cobros_superiores() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT cl.id, cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente, "
        "(SELECT COALESCE(SUM(total),0) FROM invoices "
        " WHERE client_id = cl.id AND estado <> 'anulada') AS facturado, "
        "(SELECT COALESCE(SUM(importe),0) FROM payments "
        " WHERE client_id = cl.id) AS cobrado FROM clients cl"
    )
    hallazgos = []
    for f in filas:
        facturado, cobrado = float(f["facturado"]), float(f["cobrado"])
        if cobrado - facturado > TOLERANCIA_EUR:
            hallazgos.append(Hallazgo(
                codigo="cobro_superior",
                severidad="media",
                titulo=f"{f['cliente'].strip()} ha pagado más de lo facturado",
                detalle=(f"Cobrado {cobrado:.2f} € frente a {facturado:.2f} € "
                         "facturados. Puede ser una provisión de fondos pendiente "
                         "de facturar, o un cobro mal registrado."),
                entidad=f["cliente"].strip(),
                client_id=f["id"],
            ))
    return hallazgos


# -------------------------------------------------------------------- fichas

def _fichas_incompletas() -> list[Hallazgo]:
    hallazgos = []
    sin_nif = fetch_all(
        "SELECT id, nombre || ' ' || COALESCE(apellidos,'') AS cliente FROM clients "
        "WHERE (nif IS NULL OR TRIM(nif) = '') AND activo = 1"
    )
    for f in sin_nif:
        hallazgos.append(Hallazgo(
            codigo="cliente_sin_nif",
            severidad="media",
            titulo=f"{f['cliente'].strip()} no tiene NIF",
            detalle="Sin NIF no se le puede emitir una factura válida.",
            entidad=f["cliente"].strip(), client_id=f["id"],
        ))
    sin_email = fetch_all(
        "SELECT id, nombre || ' ' || COALESCE(apellidos,'') AS cliente FROM clients "
        "WHERE (email IS NULL OR TRIM(email) = '') AND activo = 1"
    )
    for f in sin_email:
        hallazgos.append(Hallazgo(
            codigo="cliente_sin_email",
            severidad="baja",
            titulo=f"{f['cliente'].strip()} no tiene email",
            detalle="Queda fuera de cualquier comunicación o envío masivo.",
            entidad=f["cliente"].strip(), client_id=f["id"],
        ))
    return hallazgos


def _clientes_duplicados() -> list[Hallazgo]:
    hallazgos = []
    for campo, etiqueta in (("nif", "NIF"), ("email", "email")):
        filas = fetch_all(
            f"SELECT {campo} AS valor, COUNT(*) AS n, "
            "GROUP_CONCAT(nombre || ' ' || COALESCE(apellidos,''), ' | ') AS nombres "
            f"FROM clients WHERE {campo} IS NOT NULL AND TRIM({campo}) <> '' "
            f"GROUP BY LOWER(TRIM({campo})) HAVING n > 1"
        )
        for f in filas:
            hallazgos.append(Hallazgo(
                codigo="cliente_duplicado",
                severidad="media",
                titulo=f"Dos fichas comparten el mismo {etiqueta}: {f['valor']}",
                detalle=(f"Afecta a: {f['nombres']}. Unifica las fichas para no "
                         "dividir su historial ni su saldo."),
                entidad=str(f["valor"]),
            ))
    return hallazgos


# ------------------------------------------------------------------- asuntos

def _asuntos_parados() -> list[Hallazgo]:
    limite = (_hoy() - timedelta(days=MESES_INACTIVIDAD * 30)).isoformat()
    filas = fetch_all(
        "SELECT c.id, c.titulo, c.client_id, c.fecha_inicio, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente, "
        "(SELECT MAX(fecha) FROM case_events WHERE case_id = c.id) AS ultimo "
        "FROM cases c JOIN clients cl ON cl.id = c.client_id "
        "WHERE c.estado = 'abierto'"
    )
    hallazgos = []
    for f in filas:
        ultimo = (f["ultimo"] or f["fecha_inicio"] or "")[:10]
        if ultimo and ultimo < limite:
            hallazgos.append(Hallazgo(
                codigo="asunto_parado",
                severidad="alta",
                titulo=f"«{f['titulo']}» sin movimiento desde {ultimo}",
                detalle=(f"Asunto abierto de {f['cliente'].strip()} sin anotaciones "
                         f"en más de {MESES_INACTIVIDAD} meses. Comprueba plazos, "
                         "caducidad de la instancia y prescripción."),
                entidad=f["titulo"], client_id=f["client_id"],
            ))
    return hallazgos


def _gastos_sin_repercutir() -> list[Hallazgo]:
    filas = fetch_all(
        "SELECT e.id, e.concepto, e.total, e.fecha, e.client_id, "
        "cl.nombre || ' ' || COALESCE(cl.apellidos,'') AS cliente "
        "FROM expenses e JOIN clients cl ON cl.id = e.client_id "
        "WHERE e.repercutible = 1 ORDER BY e.fecha"
    )
    return [Hallazgo(
        codigo="gasto_sin_repercutir",
        severidad="media",
        titulo=f"Gasto repercutible sin facturar: {f['concepto']}",
        detalle=(f"{float(f['total']):.2f} € del {f['fecha']} marcados como "
                 f"repercutibles a {f['cliente'].strip()} y todavía sin incluir "
                 "en ninguna factura."),
        entidad=f["concepto"], client_id=f["client_id"],
    ) for f in filas]


# ------------------------------------------------------------------ conjunto

_REGLAS = (
    _facturas_vencidas,
    _huecos_numeracion,
    _irpf_incoherente,
    _totales_descuadrados,
    _facturas_sin_lineas,
    _cobros_superiores,
    _fichas_incompletas,
    _clientes_duplicados,
    _asuntos_parados,
    _gastos_sin_repercutir,
)


def auditar(client_id: int | None = None) -> list[Hallazgo]:
    """Ejecuta todas las reglas. Con client_id, filtra a ese cliente."""
    hallazgos: list[Hallazgo] = []
    for regla in _REGLAS:
        try:
            hallazgos.extend(regla())
        except Exception as e:  # una regla rota no debe tumbar la auditoría
            hallazgos.append(Hallazgo(
                codigo="regla_fallida",
                severidad="baja",
                titulo=f"No se pudo comprobar «{regla.__name__}»",
                detalle=str(e),
            ))
    if client_id is not None:
        hallazgos = [h for h in hallazgos if h.client_id == client_id]
    orden = {s: i for i, s in enumerate(SEVERIDADES)}
    hallazgos.sort(key=lambda h: (orden.get(h.severidad, 9), h.codigo))
    return hallazgos


def resumen(hallazgos: list[Hallazgo]) -> dict[str, int]:
    return {s: sum(1 for h in hallazgos if h.severidad == s) for s in SEVERIDADES}


def como_texto(hallazgos: list[Hallazgo], maximo: int = 60) -> str:
    """Formato compacto para pasárselo a la IA."""
    if not hallazgos:
        return "No se ha detectado ninguna incidencia."
    lineas = []
    for h in hallazgos[:maximo]:
        lineas.append(f"[{h.severidad.upper()}] {h.titulo} — {h.detalle}")
    if len(hallazgos) > maximo:
        lineas.append(f"(… y {len(hallazgos) - maximo} incidencias más)")
    return "\n".join(lineas)
