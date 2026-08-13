"""Proveedores de IA para el CRM.

Dos opciones seleccionables desde Ajustes:

- **Claude** (API de Anthropic): la de mayor calidad para análisis jurídico y
  comercial. Los datos que se envían salen del equipo, así que la elección es
  consciente y está avisada en la interfaz.
- **Ollama** (local): funciona sin conexión y ningún dato sale del ordenador.
  Calidad menor, pero cumple con el secreto profesional sin más trámite.

Ambos exponen la misma interfaz, de modo que el resto del programa no sabe
cuál está activo.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Iterator

import requests

from app.database.db import get_setting

# Modelo por defecto de Claude. Es el más capaz para razonamiento largo.
MODELO_CLAUDE_POR_DEFECTO = "claude-opus-5"

# Precios de lista de Claude Opus 5 (USD por millón de tokens).
# Sirven solo para estimar el coste que se muestra al usuario.
_PRECIO_ENTRADA = 5.00
_PRECIO_SALIDA = 25.00
_PRECIO_CACHE_LECTURA = 0.50    # ~0,1x entrada
_PRECIO_CACHE_ESCRITURA = 6.25  # ~1,25x entrada


class IAError(RuntimeError):
    """Fallo recuperable del proveedor de IA, con mensaje para el usuario."""


@dataclass
class RespuestaIA:
    texto: str
    proveedor: str
    modelo: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    cache_lectura: int = 0
    cache_escritura: int = 0
    aviso: str | None = None

    @property
    def coste_usd(self) -> float:
        return (
            self.tokens_entrada / 1e6 * _PRECIO_ENTRADA
            + self.tokens_salida / 1e6 * _PRECIO_SALIDA
            + self.cache_lectura / 1e6 * _PRECIO_CACHE_LECTURA
            + self.cache_escritura / 1e6 * _PRECIO_CACHE_ESCRITURA
        )

    def resumen_uso(self) -> str:
        if self.proveedor != "claude":
            return f"{self.proveedor} · {self.modelo} · sin coste (local)"
        partes = [
            f"entrada {self.tokens_entrada}",
            f"salida {self.tokens_salida}",
        ]
        if self.cache_lectura:
            partes.append(f"caché leída {self.cache_lectura}")
        if self.cache_escritura:
            partes.append(f"caché escrita {self.cache_escritura}")
        return (
            f"{self.modelo} · " + " · ".join(partes)
            + f" · ~{self.coste_usd:.4f} USD"
        )


class ProveedorIA:
    """Interfaz común. `sistema` es el bloque estable (se cachea en Claude)."""

    nombre = "base"
    etiqueta = "Base"

    def disponible(self) -> tuple[bool, str]:
        raise NotImplementedError

    def generar(self, sistema: str, prompt: str,
                max_tokens: int = 16000) -> RespuestaIA:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Ollama (local)
# --------------------------------------------------------------------------

class ProveedorOllama(ProveedorIA):
    nombre = "ollama"
    etiqueta = "Ollama (local, privado)"

    def _url(self) -> str:
        return (get_setting("ollama_url") or "http://localhost:11434").rstrip("/")

    def _modelo(self) -> str:
        return get_setting("ollama_model") or "llama3.1"

    def modelos(self) -> list[str]:
        try:
            r = requests.get(f"{self._url()}/api/tags", timeout=2)
            r.raise_for_status()
            return [m.get("name", "") for m in r.json().get("models", [])]
        except requests.RequestException:
            return []

    def disponible(self) -> tuple[bool, str]:
        try:
            r = requests.get(f"{self._url()}/api/tags", timeout=1.5)
            if r.status_code != 200:
                return False, f"Ollama respondió {r.status_code} en {self._url()}"
        except requests.RequestException:
            return False, (
                f"No se detecta Ollama en {self._url()}. Instálalo desde "
                "https://ollama.com y arranca el servicio."
            )
        modelo = self._modelo()
        instalados = self.modelos()
        if instalados and not any(m.split(":")[0] == modelo.split(":")[0]
                                  for m in instalados):
            return False, (
                f"Ollama funciona, pero el modelo «{modelo}» no está descargado.\n"
                f"Ejecuta en una terminal:  ollama pull {modelo}"
            )
        return True, f"Ollama listo · modelo {modelo}"

    def generar(self, sistema: str, prompt: str,
                max_tokens: int = 16000) -> RespuestaIA:
        ok, motivo = self.disponible()
        if not ok:
            raise IAError(motivo)
        payload = {
            "model": self._modelo(),
            "prompt": prompt,
            "system": sistema,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_tokens},
        }
        try:
            r = requests.post(f"{self._url()}/api/generate", json=payload,
                              timeout=600)
            r.raise_for_status()
            datos = r.json()
        except requests.RequestException as e:
            raise IAError(f"Error al consultar Ollama: {e}") from e
        return RespuestaIA(
            texto=(datos.get("response") or "").strip(),
            proveedor=self.nombre,
            modelo=self._modelo(),
            tokens_entrada=int(datos.get("prompt_eval_count") or 0),
            tokens_salida=int(datos.get("eval_count") or 0),
        )


# --------------------------------------------------------------------------
# Claude (API de Anthropic)
# --------------------------------------------------------------------------

class ProveedorClaude(ProveedorIA):
    nombre = "claude"
    etiqueta = "Claude (API de Anthropic)"

    def _api_key(self) -> str:
        # La variable de entorno tiene prioridad: es la forma recomendada de
        # guardar la clave, porque no queda escrita en la base de datos.
        return (os.environ.get("ANTHROPIC_API_KEY", "").strip()
                or (get_setting("claude_api_key") or "").strip())

    def _modelo(self) -> str:
        return get_setting("claude_model") or MODELO_CLAUDE_POR_DEFECTO

    def _effort(self) -> str:
        valor = (get_setting("claude_effort") or "high").strip()
        return valor if valor in ("low", "medium", "high", "xhigh", "max") else "high"

    @staticmethod
    def _modulo():
        """Importa la librería traduciendo su ausencia a un mensaje útil."""
        try:
            import anthropic
        except ImportError as e:
            raise IAError(
                "Falta la librería de Anthropic. Instálala con:\n"
                "    pip install anthropic\n"
                "o vuelve a ejecutar el actualizador del programa."
            ) from e
        return anthropic

    def _cliente(self, anthropic):
        clave = self._api_key()
        if not clave:
            raise IAError(
                "No hay clave de API de Claude configurada.\n\n"
                "Ponla en Ajustes > Inteligencia artificial, o define la "
                "variable de entorno ANTHROPIC_API_KEY (más seguro).\n"
                "Puedes obtener una en https://console.anthropic.com"
            )
        return anthropic.Anthropic(api_key=clave)

    def disponible(self) -> tuple[bool, str]:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "Falta la librería 'anthropic' (pip install anthropic)."
        if not self._api_key():
            return False, (
                "Falta la clave de API. Configúrala en Ajustes o en la "
                "variable de entorno ANTHROPIC_API_KEY."
            )
        origen = ("variable de entorno"
                  if os.environ.get("ANTHROPIC_API_KEY", "").strip()
                  else "Ajustes")
        return True, (f"Claude listo · modelo {self._modelo()} · "
                      f"esfuerzo {self._effort()} · clave desde {origen}")

    def generar(self, sistema: str, prompt: str,
                max_tokens: int = 16000) -> RespuestaIA:
        anthropic = self._modulo()
        cliente = self._cliente(anthropic)
        modelo = self._modelo()

        # El bloque de sistema es idéntico entre consultas, así que se marca
        # como cacheable: a partir de la segunda llamada se cobra ~10% de su
        # coste. Lo variable (datos del cliente, pregunta) va en el mensaje,
        # después del punto de caché, para no invalidarla.
        sistema_bloques = [{
            "type": "text",
            "text": sistema,
            "cache_control": {"type": "ephemeral"},
        }]
        comunes = {
            "model": modelo,
            "max_tokens": max_tokens,
            "system": sistema_bloques,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"effort": self._effort()},
        }

        try:
            respuesta = self._invocar(cliente, comunes)
        except anthropic.AuthenticationError as e:
            raise IAError("La clave de API de Claude no es válida.") from e
        except anthropic.PermissionDeniedError as e:
            raise IAError(
                "La clave no tiene permiso para este modelo. Revisa tu plan "
                "en console.anthropic.com."
            ) from e
        except anthropic.NotFoundError as e:
            raise IAError(f"El modelo «{modelo}» no existe o no está disponible.") from e
        except anthropic.RateLimitError as e:
            raise IAError(
                "Has superado el límite de peticiones de Claude. "
                "Espera un momento y vuelve a intentarlo."
            ) from e
        except anthropic.APIStatusError as e:
            raise IAError(f"Claude devolvió un error ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise IAError(
                "No hay conexión con la API de Claude. Comprueba tu internet."
            ) from e

        aviso = None
        if respuesta.stop_reason == "refusal":
            detalle = getattr(respuesta, "stop_details", None)
            categoria = getattr(detalle, "category", None) if detalle else None
            aviso = (
                "Claude ha declinado responder a esta consulta"
                + (f" (motivo: {categoria})" if categoria else "")
                + ". Reformula la pregunta o usa el proveedor local."
            )
        elif respuesta.stop_reason == "max_tokens":
            aviso = ("La respuesta se ha cortado por longitud. "
                     "Pide un resumen más breve o divide la consulta.")

        texto = "".join(
            bloque.text for bloque in respuesta.content
            if getattr(bloque, "type", None) == "text"
        ).strip()

        uso = respuesta.usage
        return RespuestaIA(
            texto=texto,
            proveedor=self.nombre,
            modelo=getattr(respuesta, "model", modelo),
            tokens_entrada=getattr(uso, "input_tokens", 0) or 0,
            tokens_salida=getattr(uso, "output_tokens", 0) or 0,
            cache_lectura=getattr(uso, "cache_read_input_tokens", 0) or 0,
            cache_escritura=getattr(uso, "cache_creation_input_tokens", 0) or 0,
            aviso=aviso,
        )

    @staticmethod
    def _invocar(cliente, comunes: dict):
        """Llama a la API pidiendo modelo de reserva si el servidor lo admite.

        Si una consulta es declinada por los filtros de seguridad, Anthropic la
        reintenta sola en otro modelo en la misma llamada. Si la versión de la
        librería instalada no conoce ese parámetro, se repite sin él.
        """
        try:
            return cliente.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                **comunes,
            )
        except TypeError:
            pass
        except Exception as e:  # parámetro no soportado por la cuenta o versión
            if type(e).__name__ not in ("BadRequestError", "NotFoundError"):
                raise
        return cliente.messages.create(**comunes)


# --------------------------------------------------------------------------
# Selección
# --------------------------------------------------------------------------

PROVEEDORES: dict[str, type[ProveedorIA]] = {
    ProveedorOllama.nombre: ProveedorOllama,
    ProveedorClaude.nombre: ProveedorClaude,
}


def proveedor_activo() -> ProveedorIA:
    nombre = (get_setting("ia_proveedor") or "ollama").strip()
    clase = PROVEEDORES.get(nombre, ProveedorOllama)
    return clase()


def generar(sistema: str, prompt: str, max_tokens: int = 16000) -> RespuestaIA:
    return proveedor_activo().generar(sistema, prompt, max_tokens=max_tokens)
