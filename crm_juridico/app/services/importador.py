"""Alta masiva de fichas de clientes a partir de un archivo.

Sirve para volcar de golpe la información que ya se tiene reunida fuera del
programa (expedientes de Drive, formularios de concurso, hojas de encargo)
sin teclearla ficha por ficha.

El archivo es un JSON con esta forma:

    {
      "formato": "crm-juridico/clientes",
      "version": 1,
      "clientes": [
        {
          "nombre": "...", "apellidos": "...", "nif": "...",
          "email": "...", "telefono": "...", "direccion": "...",
          "ciudad": "...", "codigo_postal": "...",
          "estado_civil": "...", "regimen_economico": "...", "notas": "...",
          "hijos": [{"nombre": "...", "fecha_nacimiento": "2020-09-12"}],
          "patrimonio": [{"categoria": "cuenta", "descripcion": "...",
                          "identificador": "ES...", "entidad": "...",
                          "valor": 0, "notas": "..."}],
          "asuntos": [{"titulo": "...", "materia": "mercantil",
                       "seguimiento": [{"titulo": "...", "detalle": "..."}]}]
        }
      ]
    }

Reglas de convivencia con lo que ya hay en la base de datos:

  * El cliente se identifica por su NIF; si no lo lleva, por nombre y
    apellidos. Importar dos veces el mismo archivo no duplica nada.
  * Por defecto NO se pisa ningún dato ya grabado: solo se rellenan los
    campos que estén vacíos. Con ``sobrescribir=True`` el archivo manda.
  * Hijos, patrimonio y asuntos se añaden solo si no constan ya.

Nada se da por bueno a ciegas: todo lo que se descarta o no se entiende
aparece en el informe que devuelve :func:`importar`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.models import cases as m_cases
from app.models import clients as m_clients
from app.models import patrimonio as m_patrimonio

FORMATO = "crm-juridico/clientes"

# Campos de texto de la ficha que el archivo puede traer.
CAMPOS_TEXTO = [
    "nombre", "apellidos", "nif", "tipo", "email", "telefono",
    "direccion", "ciudad", "codigo_postal", "pais", "notas",
    "estado_civil", "regimen_economico",
]


class ImportError_(Exception):
    """El archivo no se puede leer o no tiene el formato esperado."""


@dataclass
class Resultado:
    """Qué ha pasado con cada ficha, para poder enseñárselo al usuario."""

    creados: int = 0
    actualizados: int = 0
    sin_cambios: int = 0
    hijos: int = 0
    bienes: int = 0
    asuntos: int = 0
    anotaciones: int = 0
    detalle: list = field(default_factory=list)   # una línea por cliente
    avisos: list = field(default_factory=list)    # problemas no fatales

    @property
    def total(self) -> int:
        return self.creados + self.actualizados + self.sin_cambios

    def como_texto(self) -> str:
        lineas = list(self.detalle)
        if self.avisos:
            lineas.append("")
            lineas.append("AVISOS")
            lineas.extend(f"  · {a}" for a in self.avisos)
        lineas.append("")
        lineas.append(
            f"Fichas nuevas: {self.creados}   "
            f"actualizadas: {self.actualizados}   "
            f"sin cambios: {self.sin_cambios}"
        )
        lineas.append(
            f"Hijos: {self.hijos}   Patrimonio: {self.bienes}   "
            f"Asuntos: {self.asuntos}   Anotaciones: {self.anotaciones}"
        )
        return "\n".join(lineas)


# ---------- Lectura del archivo ----------

def leer(ruta: str | Path) -> list:
    """Devuelve la lista de clientes del archivo, ya validada por encima."""
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as e:
        raise ImportError_(f"No se ha podido abrir el archivo:\n{e}") from e
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ImportError_(
            "El archivo no es un JSON válido.\n"
            f"Línea {e.lineno}, columna {e.colno}: {e.msg}"
        ) from e

    if isinstance(datos, list):
        clientes = datos            # se admite la lista pelada
    elif isinstance(datos, dict):
        formato = datos.get("formato")
        if formato and formato != FORMATO:
            raise ImportError_(
                f"El archivo dice ser de formato «{formato}», y aquí se "
                f"espera «{FORMATO}»."
            )
        clientes = datos.get("clientes")
    else:
        raise ImportError_("El archivo no contiene una lista de clientes.")

    if not isinstance(clientes, list):
        raise ImportError_("El archivo no contiene una lista de clientes.")
    if not clientes:
        raise ImportError_("El archivo no trae ningún cliente.")
    for c in clientes:
        if not isinstance(c, dict):
            raise ImportError_("Cada cliente debe ser un bloque de datos.")
        if not (c.get("nombre") or "").strip():
            raise ImportError_("Hay un cliente sin nombre en el archivo.")
    return clientes


def resumen(clientes: list) -> str:
    """Vista previa: qué se va a crear y qué ya existe. No toca nada."""
    lineas = []
    for c in clientes:
        existente = _buscar(c)
        marca = "actualizar" if existente else "NUEVO"
        extras = []
        if c.get("hijos"):
            extras.append(f"{len(c['hijos'])} hijos")
        if c.get("patrimonio"):
            extras.append(f"{len(c['patrimonio'])} bienes/deudas")
        if c.get("asuntos"):
            extras.append(f"{len(c['asuntos'])} asuntos")
        cola = f"  ({', '.join(extras)})" if extras else ""
        lineas.append(f"  [{marca}] {_nombre(c)}{cola}")
    return "\n".join(lineas)


# ---------- Importación ----------

def importar(clientes: list, sobrescribir: bool = False) -> Resultado:
    """Vuelca los clientes en la base de datos y devuelve el informe.

    Un fallo en una ficha no detiene las demás: se anota como aviso y se
    sigue con la siguiente.
    """
    res = Resultado()
    for c in clientes:
        try:
            _importar_uno(c, sobrescribir, res)
        except Exception as e:                      # noqa: BLE001
            res.avisos.append(f"{_nombre(c)}: no se ha podido importar ({e})")
    return res


def _importar_uno(c: dict, sobrescribir: bool, res: Resultado) -> None:
    existente = _buscar(c)
    campos = _campos_ficha(c)

    if existente is None:
        client_id = m_clients.create_client(campos)
        res.creados += 1
        estado = "creada"
    else:
        client_id = existente["id"]
        cambios = _campos_a_actualizar(existente, campos, sobrescribir)
        if cambios:
            m_clients.update_client_fields(client_id, cambios)
            res.actualizados += 1
            estado = f"actualizada ({', '.join(sorted(cambios))})"
        else:
            res.sin_cambios += 1
            estado = "ya estaba al día"

    n_hijos = _importar_hijos(client_id, c.get("hijos") or [], res)
    n_bienes = _importar_patrimonio(client_id, c.get("patrimonio") or [], res)
    n_asuntos = _importar_asuntos(client_id, c.get("asuntos") or [], res)

    añadido = []
    if n_hijos:
        añadido.append(f"+{n_hijos} hijos")
    if n_bienes:
        añadido.append(f"+{n_bienes} patrimonio")
    if n_asuntos:
        añadido.append(f"+{n_asuntos} asuntos")
    cola = f"  {', '.join(añadido)}" if añadido else ""
    res.detalle.append(f"  {_nombre(c)}: {estado}{cola}")


def _importar_hijos(client_id: int, hijos: list, res: Resultado) -> int:
    ya = {_clave(h["nombre"]) for h in m_patrimonio.list_children(client_id)}
    nuevos = 0
    for h in hijos:
        nombre = (h.get("nombre") or "").strip()
        if not nombre:
            res.avisos.append("Se ha ignorado un hijo sin nombre.")
            continue
        if _clave(nombre) in ya:
            continue
        m_patrimonio.create_child(
            client_id, nombre,
            h.get("fecha_nacimiento") or None,
            h.get("notas") or "",
        )
        ya.add(_clave(nombre))
        nuevos += 1
    res.hijos += nuevos
    return nuevos


def _clave_bien(categoria, identificador, entidad, descripcion) -> tuple:
    """Cómo se reconoce un bien ya grabado.

    Con identificador (matrícula, IBAN, nº de préstamo) basta con él. Sin él
    hay que mirar también el acreedor: varias deudas de un mismo cliente
    pueden compartir descripción («préstamo al consumo») y ser distintas.
    """
    ident = _clave(identificador)
    if ident:
        return (categoria, ident)
    return (categoria, _clave(entidad), _clave(descripcion))


def _importar_patrimonio(client_id: int, bienes: list, res: Resultado) -> int:
    ya = {
        _clave_bien(b["categoria"], b["identificador"], b["entidad"],
                    b["descripcion"])
        for b in m_patrimonio.list_assets(client_id)
    }
    nuevos = 0
    for b in bienes:
        categoria = (b.get("categoria") or "").strip().lower()
        descripcion = (b.get("descripcion") or "").strip()
        if categoria not in m_patrimonio.CATEGORIAS:
            res.avisos.append(
                f"Categoría de patrimonio desconocida: «{b.get('categoria')}». "
                f"Válidas: {', '.join(m_patrimonio.CATEGORIAS)}."
            )
            continue
        if not descripcion:
            res.avisos.append(f"Se ha ignorado un/a {categoria} sin descripción.")
            continue
        clave = _clave_bien(categoria, b.get("identificador"),
                            b.get("entidad"), descripcion)
        if clave in ya:
            continue
        m_patrimonio.create_asset({
            "client_id": client_id,
            "categoria": categoria,
            "descripcion": descripcion,
            "identificador": b.get("identificador") or "",
            "entidad": b.get("entidad") or "",
            "valor": _numero(b.get("valor")),
            "fecha": b.get("fecha") or None,
            "notas": b.get("notas") or "",
        })
        ya.add(clave)
        nuevos += 1
    res.bienes += nuevos
    return nuevos


def _importar_asuntos(client_id: int, asuntos: list, res: Resultado) -> int:
    ya = {
        _clave(a["titulo"]): a["id"]
        for a in m_cases.list_cases_by_client(client_id)
    }
    nuevos = 0
    for a in asuntos:
        titulo = (a.get("titulo") or "").strip()
        if not titulo:
            res.avisos.append("Se ha ignorado un asunto sin título.")
            continue
        case_id = ya.get(_clave(titulo))
        if case_id is None:
            case_id = m_cases.create_case({
                "client_id": client_id,
                "referencia": a.get("referencia") or "",
                "titulo": titulo,
                "materia": a.get("materia") or "",
                "estado": a.get("estado") or "abierto",
                "juzgado": a.get("juzgado") or "",
                "numero_autos": a.get("numero_autos") or "",
                "fecha_inicio": a.get("fecha_inicio") or None,
                "fecha_cierre": a.get("fecha_cierre") or None,
                "descripcion": a.get("descripcion") or "",
            })
            ya[_clave(titulo)] = case_id
            nuevos += 1
        res.anotaciones += _importar_seguimiento(
            case_id, a.get("seguimiento") or [], res
        )
    res.asuntos += nuevos
    return nuevos


def _importar_seguimiento(case_id: int, entradas: list, res: Resultado) -> int:
    ya = {_clave(e["titulo"]) for e in m_cases.list_events(case_id)}
    nuevas = 0
    for e in entradas:
        titulo = (e.get("titulo") or "").strip()
        if not titulo:
            res.avisos.append("Se ha ignorado una anotación sin título.")
            continue
        if _clave(titulo) in ya:
            continue
        m_cases.add_event(
            case_id,
            e.get("tipo") or "nota",
            titulo,
            e.get("detalle") or "",
            e.get("fecha") or None,
        )
        ya.add(_clave(titulo))
        nuevas += 1
    return nuevas


# ---------- Utilidades ----------

def _nombre(c: dict) -> str:
    return f"{c.get('nombre', '')} {c.get('apellidos') or ''}".strip()


def _clave(texto) -> str:
    """Normaliza un texto para comparar sin tropezar con mayúsculas ni espacios."""
    return " ".join((texto or "").split()).casefold()


def _clave_nif(nif) -> str:
    """El NIF, sin guiones ni espacios y en mayúsculas: 77117800-L = 77117800L."""
    return "".join(ch for ch in (nif or "") if ch.isalnum()).upper()


def _numero(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _campos_ficha(c: dict) -> dict:
    """Extrae de la entrada del archivo solo las columnas de la ficha."""
    campos = {
        k: str(c[k]).strip()
        for k in CAMPOS_TEXTO
        if c.get(k) not in (None, "")
    }
    campos.setdefault("tipo", "particular")
    campos.setdefault("pais", "España")
    if "irpf_nuevo" in c:
        campos["irpf_nuevo"] = 1 if c["irpf_nuevo"] else 0
    return campos


def _campos_a_actualizar(existente, campos: dict, sobrescribir: bool) -> dict:
    """Qué campos de una ficha ya existente hay que tocar.

    Sin ``sobrescribir`` solo se rellenan los huecos: lo que el usuario haya
    escrito en el programa siempre gana sobre lo que traiga el archivo.
    """
    cambios = {}
    for campo, nuevo in campos.items():
        try:
            actual = existente[campo]
        except (IndexError, KeyError):
            continue
        actual = (actual or "") if isinstance(actual, str) else actual
        if sobrescribir:
            if str(actual or "") != str(nuevo):
                cambios[campo] = nuevo
        elif not actual:
            cambios[campo] = nuevo
    return cambios


def _buscar(c: dict):
    """Localiza la ficha ya existente: primero por NIF, luego por nombre."""
    nif = _clave_nif(c.get("nif"))
    if nif:
        for fila in m_clients.list_clients():
            if _clave_nif(fila["nif"]) == nif:
                return m_clients.get_client(fila["id"])
    nombre = _clave(c.get("nombre"))
    apellidos = _clave(c.get("apellidos"))
    for fila in m_clients.list_clients():
        if _clave(fila["nombre"]) == nombre and _clave(fila["apellidos"]) == apellidos:
            return m_clients.get_client(fila["id"])
    return None
