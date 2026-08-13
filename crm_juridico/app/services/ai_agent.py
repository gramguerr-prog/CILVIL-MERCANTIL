"""Agente de IA del despacho.

Todo pasa por `ai_provider`, así que funciona igual con Claude o con Ollama.

El prompt de sistema es largo y **estable entre consultas**: eso es
deliberado, porque con Claude se marca como cacheable y a partir de la segunda
consulta su coste baja a una décima parte. Lo que cambia en cada consulta (los
datos del cliente, la pregunta) va siempre en el mensaje, nunca en el sistema,
para no invalidar esa caché.
"""
from __future__ import annotations

from app.database.db import get_setting
from app.models import cases as m_cases
from app.models import clients as m_clients
from app.models import expenses as m_expenses
from app.models import invoices as m_invoices
from app.models import patrimonio as m_patrimonio
from app.services import auditoria
from app.services.ai_provider import IAError, RespuestaIA, generar  # noqa: F401


def _cabecera_despacho() -> str:
    nombre = get_setting("despacho_nombre") or "un despacho de abogados"
    ciudad = get_setting("despacho_direccion") or ""
    return f"{nombre}{f', {ciudad}' if ciudad else ''}"


SISTEMA = f"""Eres el asistente interno de {_cabecera_despacho()}, un despacho \
de abogados que ejerce en España. Trabajas para el abogado titular, no para el \
cliente final: tus respuestas son de uso interno y puedes ser directo.

MARCO DE TRABAJO
- Ordenamiento español: Código Civil, Código de Comercio, LEC, LGT, Ley del IVA \
y Ley del IRPF, normativa de consumidores y de segunda oportunidad, entre otras.
- Cuando cites una norma, indícala por su nombre y artículo. Si no estás seguro \
de la referencia exacta, dilo en lugar de inventarla: una cita falsa es peor que \
ninguna cita.
- No eres el abogado del asunto. Señalas opciones, riesgos y plazos; la decisión \
y la firma son siempre del titular.

REGLA PRINCIPAL SOBRE LOS DATOS
Trabajas exclusivamente con los datos que se te entregan en cada consulta. No \
supongas ingresos, bienes, fechas ni antecedentes que no aparezcan. Cuando falte \
un dato relevante para la conclusión, dilo explícitamente y señala qué haría \
falta averiguar. Si los datos aportados se contradicen entre sí, hazlo constar en \
lugar de elegir uno en silencio.

CÓMO ESCRIBES
- Español de España, registro profesional, sin florituras ni frases de relleno.
- Empieza por la conclusión. El detalle va después, para quien quiera leerlo.
- Prosa por defecto; listas solo cuando enumeras elementos realmente paralelos, \
y tablas solo para datos cortos y comparables.
- Sin preámbulos del tipo "claro", "por supuesto" ni resúmenes de lo que te han \
preguntado. Responde.
- Cifras en euros con dos decimales y separador de miles. Fechas en formato \
día/mes/año.
- Extensión proporcionada a la pregunta: una consulta concreta se responde en un \
párrafo, no en tres páginas.

CRITERIO ECONÓMICO Y FISCAL
- IVA general del 21 %; reducido del 10 %; superreducido del 4 %.
- La retención de IRPF solo se practica cuando el destinatario de la factura es \
empresa o profesional (operación B2B). A un particular nunca se le retiene.
- Retención profesional general del 15 %, o del 7 % durante los tres primeros \
años de actividad.
- La numeración de facturas debe ser correlativa y sin saltos; una factura \
anulada se conserva anulada, no se borra.

CRITERIO COMERCIAL
Cuando propongas servicios adicionales a un cliente, cada propuesta debe apoyarse \
en un dato concreto de su ficha, no en generalidades. Cruza su situación real con \
lo que el despacho puede ofrecerle. Ejemplos de razonamiento válido: hijos menores \
apuntan a testamento y planificación sucesoria; una hipoteca abre la revisión de \
cláusulas y la reclamación de gastos; ser propietario de inmuebles arrastra \
arrendamientos, fiscalidad, IBI y plusvalía municipal; un endeudamiento alto sin \
patrimonio que lo respalde apunta a refinanciación o a la Ley de Segunda \
Oportunidad; los vehículos traen siniestros y sanciones de tráfico; una sociedad \
mercantil arrastra contratos, laboral, protección de datos y responsabilidad de \
administradores. Si un cliente no tiene datos suficientes para sostener ninguna \
propuesta, dilo y señala qué habría que preguntarle en la próxima visita.

Sé honesto sobre lo que los datos no permiten concluir. Es más útil un "con esta \
información no se puede determinar" que una respuesta segura y equivocada."""


# --------------------------------------------------------------------- fichas

def contexto_cliente(client_id: int) -> str:
    """Expediente completo del cliente en texto, para pasárselo a la IA."""
    c = m_clients.get_client(client_id)
    if c is None:
        return "Cliente no encontrado."

    saldo = m_clients.client_balance(client_id)
    pat = m_patrimonio.patrimonio_summary(client_id)
    hijos = m_patrimonio.list_children(client_id)
    asuntos = m_cases.list_cases_by_client(client_id)
    facturas = m_invoices.list_invoices_by_client(client_id)
    gastos = m_expenses.list_expenses_by_client(client_id)

    p = [
        "== FICHA DEL CLIENTE ==",
        f"Nombre: {c['nombre']} {c['apellidos'] or ''}".strip(),
        f"Tipo: {c['tipo']} · NIF: {c['nif'] or 'no consta'}",
        f"Ciudad: {c['ciudad'] or 'no consta'} · Email: {c['email'] or 'no consta'}"
        f" · Teléfono: {c['telefono'] or 'no consta'}",
        f"Cliente desde: {c['fecha_alta']}",
        f"Estado civil: {c['estado_civil'] or 'no consta'} · "
        f"Régimen económico: {c['regimen_economico'] or 'no consta'}",
        f"Notas internas: {c['notas'] or '—'}",
        "",
        "== FAMILIA ==",
    ]
    if hijos:
        for h in hijos:
            p.append(f"- {h['nombre'] or 'sin nombre'}"
                     + (f", nacido/a el {h['fecha_nacimiento']}"
                        if h["fecha_nacimiento"] else "")
                     + (f" ({h['notas']})" if h["notas"] else ""))
    else:
        p.append("No constan hijos registrados."
                 if not c["tiene_hijos"]
                 else "Marcado como «tiene hijos», pero sin detalle registrado.")

    p += ["", "== PATRIMONIO Y CARGAS =="]
    etiquetas = {"vehiculo": "Vehículos", "cuenta": "Cuentas corrientes",
                 "hipoteca": "Hipotecas", "propiedad": "Propiedades",
                 "deuda": "Deudas"}
    hay_patrimonio = False
    for clave, etiqueta in etiquetas.items():
        bienes = m_patrimonio.list_assets(client_id, clave)
        if not bienes:
            continue
        hay_patrimonio = True
        p.append(f"{etiqueta}:")
        for b in bienes:
            linea = f"  - {b['descripcion']}"
            if b["entidad"]:
                linea += f" ({b['entidad']})"
            if b["valor"]:
                linea += f" — {float(b['valor']):,.2f} €"
            if b["notas"]:
                linea += f" · {b['notas']}"
            p.append(linea)
    if not hay_patrimonio:
        p.append("No consta ningún bien ni carga registrada.")
    p.append(f"Activo {pat['activo']:,.2f} € · Cargas y deudas "
             f"{pat['pasivo']:,.2f} € · Patrimonio neto {pat['neto']:,.2f} €")

    p += ["", "== ASUNTOS =="]
    if asuntos:
        for a in asuntos:
            p.append(f"- [{a['estado']}] {a['titulo']} ({a['materia'] or 'sin materia'}), "
                     f"desde {a['fecha_inicio']}")
            for e in m_cases.list_events(a["id"])[:5]:
                p.append(f"    · {e['fecha'][:10]} {e['tipo'] or ''}: {e['titulo']}")
    else:
        p.append("Sin asuntos registrados.")

    p += ["", "== ECONOMÍA DE LA RELACIÓN ==",
          f"Facturado {saldo['facturado']:,.2f} € · Cobrado {saldo['cobrado']:,.2f} € "
          f"· Pendiente {saldo['pendiente']:,.2f} €",
          f"Facturas emitidas: {len(facturas)}"]
    for f in facturas[:10]:
        p.append(f"  - {f['numero']} ({f['fecha_emision']}): "
                 f"{float(f['total']):,.2f} € [{f['estado']}]")
    if gastos:
        p.append(f"Gastos imputados: {len(gastos)}")
        for g in gastos[:10]:
            p.append(f"  - {g['fecha']} {g['concepto']}: {float(g['total']):,.2f} €"
                     + (" (repercutible)" if g["repercutible"] else ""))

    incidencias = auditoria.auditar(client_id=client_id)
    if incidencias:
        p += ["", "== INCIDENCIAS DETECTADAS EN SUS DATOS =="]
        p.append(auditoria.como_texto(incidencias, maximo=15))

    return "\n".join(p)


# ------------------------------------------------------------------ análisis

def analizar_perfil(client_id: int) -> RespuestaIA:
    prompt = (
        "Analiza el perfil de este cliente para uso interno del despacho. "
        "Estructura la respuesta así:\n"
        "1) Retrato en tres o cuatro frases: quién es y qué relación tiene con "
        "el despacho.\n"
        "2) Situación jurídica: qué asuntos tiene abiertos, en qué estado, y qué "
        "riesgos o plazos deberían vigilarse.\n"
        "3) Situación económica de la relación: qué ha facturado, qué debe, y si "
        "hay algo que corregir.\n"
        "4) Huecos de información: qué datos faltan en la ficha y por qué importan.\n\n"
        + contexto_cliente(client_id)
    )
    return generar(SISTEMA, prompt)


def propuesta_comercial(client_id: int) -> RespuestaIA:
    prompt = (
        "Prepara una propuesta comercial personalizada para este cliente. "
        "Estructura la respuesta así:\n"
        "1) Diagnóstico en dos o tres frases.\n"
        "2) Entre tres y cinco servicios legales concretos que ofrecerle, "
        "ordenados por probabilidad de que los contrate. Cada uno con: el "
        "servicio, el dato de su ficha que lo justifica, y una estimación de "
        "urgencia (ahora / este año / a vigilar).\n"
        "3) Cómo plantearlo: por qué canal, con qué mensaje de apertura y en qué "
        "momento.\n"
        "4) Qué NO conviene ofrecerle ahora y por qué.\n\n"
        + contexto_cliente(client_id)
    )
    return generar(SISTEMA, prompt)


def explicar_auditoria(hallazgos: list) -> RespuestaIA:
    resumen = auditoria.resumen(hallazgos)
    prompt = (
        "El programa ha revisado automáticamente los datos del despacho y ha "
        "detectado las incidencias que van al final. Son hechos comprobados, no "
        "conjeturas: no las pongas en duda ni añadas otras que no aparezcan.\n\n"
        "Tu trabajo es convertirlas en un plan de acción:\n"
        "1) Qué hay que resolver esta misma semana y por qué (riesgo fiscal, "
        "prescripción, dinero que se está perdiendo).\n"
        "2) Qué puede esperar, agrupado por tipo de problema.\n"
        "3) Si varias incidencias apuntan a un mismo fallo de método en cómo se "
        "lleva el despacho, señálalo: importa más que las incidencias sueltas.\n\n"
        f"Recuento: {resumen['alta']} de gravedad alta, {resumen['media']} media, "
        f"{resumen['baja']} baja.\n\n"
        "== INCIDENCIAS ==\n"
        + auditoria.como_texto(hallazgos)
    )
    return generar(SISTEMA, prompt)


def oportunidades_cartera(limite: int = 25) -> RespuestaIA:
    """Barrido comercial de toda la cartera, no de un cliente suelto."""
    filas = m_clients.list_clients(only_active=True)[:limite]
    bloques = []
    for c in filas:
        cid = c["id"]
        pat = m_patrimonio.patrimonio_summary(cid)
        ficha = m_clients.get_client(cid)
        asuntos = m_cases.list_cases_by_client(cid)
        materias = sorted({a["materia"] for a in asuntos if a["materia"]})
        bloques.append(
            f"- {c['nombre']} {c['apellidos'] or ''} ({c['tipo']}): "
            f"hijos={'sí' if ficha['tiene_hijos'] else 'no'}, "
            f"estado civil={ficha['estado_civil'] or 'n/c'}, "
            f"propiedades={'sí' if ficha['tiene_propiedades'] else 'no'}, "
            f"hipoteca={'sí' if ficha['tiene_hipotecas'] else 'no'}, "
            f"deudas={'sí' if ficha['tiene_deudas'] else 'no'}, "
            f"activo={pat['activo']:,.0f} €, pasivo={pat['pasivo']:,.0f} €, "
            f"materias trabajadas={', '.join(materias) or 'ninguna'}"
        )
    prompt = (
        "Aquí tienes la cartera de clientes activos del despacho con su "
        "situación resumida. Identifica oportunidades comerciales a nivel de "
        "cartera, no cliente por cliente:\n"
        "1) Grupos de clientes que comparten una misma necesidad legal probable, "
        "con los nombres concretos de cada grupo.\n"
        "2) Para cada grupo, qué servicio ofrecerles y cómo plantear una acción "
        "conjunta (una circular, una jornada, un email tipo).\n"
        "3) Los tres clientes con mayor potencial individual y por qué.\n\n"
        "== CARTERA ==\n" + "\n".join(bloques)
    )
    return generar(SISTEMA, prompt)


# ----------------------------------------------------------------- documentos

def resumir_documento(texto: str, nombre: str = "") -> RespuestaIA:
    prompt = (
        f"Resume este documento jurídico{f' ({nombre})' if nombre else ''}. "
        "Empieza con un resumen ejecutivo de cinco a diez líneas y sigue con los "
        "puntos clave: partes intervinientes, objeto, fechas relevantes, "
        "pretensiones, cuantías, plazos procesales y riesgos. Si el documento "
        "está incompleto o ilegible en alguna parte, dilo.\n\n"
        "== DOCUMENTO ==\n" + texto
    )
    return generar(SISTEMA, prompt)


def preguntar_documento(texto: str, pregunta: str) -> RespuestaIA:
    prompt = (
        "Responde a la pregunta basándote exclusivamente en el documento que "
        "va debajo. Si la respuesta no está en él, dilo claramente en lugar de "
        "deducirla.\n\n"
        f"PREGUNTA: {pregunta}\n\n"
        "== DOCUMENTO ==\n" + texto
    )
    return generar(SISTEMA, prompt)


def consulta_libre(pregunta: str, contexto: str = "") -> RespuestaIA:
    prompt = pregunta if not contexto else f"{pregunta}\n\n== CONTEXTO ==\n{contexto}"
    return generar(SISTEMA, prompt)
