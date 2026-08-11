"""Agente de IA local mediante Ollama.

Funciona sin enviar datos a internet: requiere Ollama instalado en localhost
con al menos un modelo descargado (ej. `ollama pull llama3.1`).
"""
import json
from typing import Iterator

import requests

from app.database.db import get_setting


class OllamaUnavailable(RuntimeError):
    pass


def _url() -> str:
    return (get_setting("ollama_url") or "http://localhost:11434").rstrip("/")


def _model() -> str:
    return get_setting("ollama_model") or "llama3.1"


def is_available(timeout: float = 1.0) -> bool:
    try:
        r = requests.get(f"{_url()}/api/tags", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def list_models() -> list[str]:
    try:
        r = requests.get(f"{_url()}/api/tags", timeout=2)
        r.raise_for_status()
        data = r.json()
        return [m.get("name", "") for m in data.get("models", [])]
    except requests.RequestException:
        return []


def generate(prompt: str, system: str | None = None,
             temperature: float = 0.2, timeout: float = 120) -> str:
    if not is_available(timeout=1.5):
        raise OllamaUnavailable(
            "No se detecta Ollama corriendo en " + _url() +
            ". Instálalo desde https://ollama.com y arranca el servicio."
        )
    payload = {
        "model": _model(),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    r = requests.post(f"{_url()}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def stream_generate(prompt: str, system: str | None = None,
                    temperature: float = 0.2) -> Iterator[str]:
    if not is_available(timeout=1.5):
        raise OllamaUnavailable("Ollama no disponible")
    payload = {
        "model": _model(),
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    with requests.post(f"{_url()}/api/generate", json=payload,
                       stream=True, timeout=600) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            piece = chunk.get("response", "")
            if piece:
                yield piece
            if chunk.get("done"):
                break


SYSTEM_PROMPT_LEGAL = (
    "Eres un asistente jurídico para un despacho de abogados en España. "
    "Respondes en español de forma clara, precisa y orientada a la práctica. "
    "Cuando resumas documentos, identifica: partes, objeto, fechas clave, "
    "pretensiones, cuantías, plazos procesales y riesgos. "
    "Si no estás seguro de un dato, dilo expresamente."
)


def summarize_document(text: str) -> str:
    prompt = (
        "Resume el siguiente documento jurídico en español. "
        "Da un resumen ejecutivo (5-10 líneas) y luego un listado de "
        "puntos clave (partes, fechas, pretensiones, plazos, riesgos).\n\n"
        "DOCUMENTO:\n" + text
    )
    return generate(prompt, system=SYSTEM_PROMPT_LEGAL, temperature=0.2)


def ask_about_document(text: str, question: str) -> str:
    prompt = (
        "Responde a la pregunta del usuario basándote exclusivamente en el "
        "documento aportado. Si la respuesta no está en el documento, dilo.\n\n"
        f"DOCUMENTO:\n{text}\n\nPREGUNTA: {question}"
    )
    return generate(prompt, system=SYSTEM_PROMPT_LEGAL, temperature=0.2)


def _format_patrimonio(patrimonio: dict | None, hijos: list[dict] | None) -> str:
    """Bloque de texto con la situación familiar y patrimonial del cliente."""
    if not patrimonio and not hijos:
        return "No consta información familiar ni patrimonial registrada.\n"

    etiquetas = {
        "vehiculo": "Vehículos",
        "cuenta": "Cuentas corrientes",
        "hipoteca": "Hipotecas",
        "propiedad": "Propiedades",
        "deuda": "Deudas",
    }
    partes: list[str] = []
    if hijos:
        detalle = ", ".join(
            f"{h.get('nombre') or 'sin nombre'}"
            + (f" (nac. {h['fecha_nacimiento']})" if h.get("fecha_nacimiento") else "")
            for h in hijos
        )
        partes.append(f"- Hijos: {len(hijos)} — {detalle}")
    else:
        partes.append("- Hijos: no constan")

    if patrimonio:
        por_categoria = patrimonio.get("por_categoria", {})
        for clave, etiqueta in etiquetas.items():
            info = por_categoria.get(clave)
            if info and info.get("n"):
                partes.append(
                    f"- {etiqueta}: {info['n']} registro(s), "
                    f"valor total {info['total']:.2f} €"
                )
            else:
                partes.append(f"- {etiqueta}: no constan")
        partes.append(
            f"- Activo estimado: {patrimonio.get('activo', 0):.2f} € · "
            f"Cargas y deudas: {patrimonio.get('pasivo', 0):.2f} € · "
            f"Patrimonio neto: {patrimonio.get('neto', 0):.2f} €"
        )
    return "\n".join(partes) + "\n"


def commercial_proposal(client_info: dict, cases: list[dict],
                        invoices_summary: dict,
                        patrimonio: dict | None = None,
                        hijos: list[dict] | None = None) -> str:
    materias = sorted({c.get("materia") or "" for c in cases if c.get("materia")})
    materias_str = ", ".join(m for m in materias if m) or "sin asuntos previos"
    titulos = "\n".join(f"- {c.get('titulo')} ({c.get('estado')})" for c in cases) or "Sin asuntos."
    prompt = (
        "Eres responsable comercial de un despacho de abogados en España. "
        "Genera una propuesta de servicios legales adicionales para este "
        "cliente, justificada según su perfil, su situación familiar y "
        "patrimonial y los asuntos ya gestionados. Cruza los datos: por "
        "ejemplo, hijos menores sugieren testamento y planificación sucesoria; "
        "hipoteca sugiere revisión de cláusulas y posible reclamación de "
        "gastos; propiedades sugieren arrendamientos, fiscalidad e IBI/plusvalía; "
        "deudas elevadas sugieren refinanciación o Ley de Segunda Oportunidad; "
        "vehículos sugieren siniestros y sanciones de tráfico. "
        "Devuélvelo en este formato:\n"
        "1) Diagnóstico breve del cliente.\n"
        "2) Lista priorizada de 3-5 servicios adicionales recomendados, cada "
        "uno con una frase de justificación anclada en un dato concreto del "
        "cliente.\n"
        "3) Sugerencia de abordaje comercial (canal, mensaje, momento).\n"
        "No inventes datos que no aparezcan abajo; si algo no consta, dilo.\n\n"
        f"DATOS DEL CLIENTE:\n"
        f"- Nombre: {client_info.get('nombre','')} {client_info.get('apellidos','') or ''}\n"
        f"- Tipo: {client_info.get('tipo','')}\n"
        f"- NIF: {client_info.get('nif','')}\n"
        f"- Ciudad: {client_info.get('ciudad','')}\n"
        f"- Estado civil: {client_info.get('estado_civil') or 'no consta'}\n"
        f"- Régimen económico: {client_info.get('regimen_economico') or 'no consta'}\n"
        f"- Notas internas: {client_info.get('notas','') or '—'}\n"
        f"- Materias trabajadas: {materias_str}\n\n"
        f"SITUACIÓN FAMILIAR Y PATRIMONIAL:\n"
        f"{_format_patrimonio(patrimonio, hijos)}\n"
        f"ASUNTOS:\n{titulos}\n\n"
        f"DATOS ECONÓMICOS DE LA RELACIÓN:\n"
        f"- Facturado: {invoices_summary.get('facturado',0):.2f} €\n"
        f"- Cobrado:   {invoices_summary.get('cobrado',0):.2f} €\n"
        f"- Pendiente: {invoices_summary.get('pendiente',0):.2f} €\n"
    )
    return generate(prompt, system=SYSTEM_PROMPT_LEGAL, temperature=0.5)
