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


def commercial_proposal(client_info: dict, cases: list[dict],
                        invoices_summary: dict) -> str:
    materias = sorted({c.get("materia") or "" for c in cases if c.get("materia")})
    materias_str = ", ".join(m for m in materias if m) or "sin asuntos previos"
    titulos = "\n".join(f"- {c.get('titulo')} ({c.get('estado')})" for c in cases) or "Sin asuntos."
    prompt = (
        "Eres responsable comercial de un despacho. Genera una propuesta de "
        "servicios legales adicionales para este cliente, justificada según su "
        "perfil y los asuntos ya gestionados. Devuélvelo en formato:\n"
        "1) Diagnóstico breve del cliente.\n"
        "2) Lista priorizada de 3-5 servicios adicionales recomendados con "
        "una frase de justificación cada uno.\n"
        "3) Sugerencia de abordaje comercial (canal, mensaje, momento).\n\n"
        f"DATOS DEL CLIENTE:\n"
        f"- Nombre: {client_info.get('nombre','')} {client_info.get('apellidos','') or ''}\n"
        f"- Tipo: {client_info.get('tipo','')}\n"
        f"- NIF: {client_info.get('nif','')}\n"
        f"- Ciudad: {client_info.get('ciudad','')}\n"
        f"- Notas internas: {client_info.get('notas','') or '—'}\n"
        f"- Materias trabajadas: {materias_str}\n"
        f"ASUNTOS:\n{titulos}\n\n"
        f"DATOS ECONÓMICOS:\n"
        f"- Facturado: {invoices_summary.get('facturado',0):.2f} €\n"
        f"- Cobrado:   {invoices_summary.get('cobrado',0):.2f} €\n"
        f"- Pendiente: {invoices_summary.get('pendiente',0):.2f} €\n"
    )
    return generate(prompt, system=SYSTEM_PROMPT_LEGAL, temperature=0.5)
