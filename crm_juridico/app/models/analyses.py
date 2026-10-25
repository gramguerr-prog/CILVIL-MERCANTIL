"""Análisis de perfil y propuestas comerciales guardadas de cada cliente.

Lo que la IA genera se pierde al cerrar la ficha si no se guarda. Aquí queda
el histórico: qué se le propuso a cada cliente, cuándo y con qué modelo, de
modo que en la siguiente visita se pueda retomar en lugar de empezar de cero.

El texto guardado es el que haya en pantalla, no necesariamente el que
devolvió la IA: la idea es que el letrado lo revise y lo corrija antes de
guardarlo.
"""

from __future__ import annotations

from app.database.db import execute, fetch_all, fetch_one

# tipo -> etiqueta que se enseña en el histórico
TIPOS = {
    "perfil": "Análisis de perfil",
    "propuesta": "Propuesta comercial",
    "manual": "Redactado a mano",
}


def list_analyses(client_id: int) -> list:
    """Los análisis del cliente, del más reciente al más antiguo."""
    return fetch_all(
        "SELECT id, fecha, tipo, modelo_usado, contenido "
        "FROM commercial_analyses WHERE client_id = ? "
        "ORDER BY fecha DESC, id DESC",
        (client_id,),
    )


def get_analysis(analysis_id: int):
    return fetch_one(
        "SELECT * FROM commercial_analyses WHERE id = ?", (analysis_id,)
    )


def create_analysis(client_id: int, contenido: str, tipo: str = "manual",
                    modelo_usado: str = "") -> int:
    return execute(
        "INSERT INTO commercial_analyses(client_id, contenido, tipo, modelo_usado) "
        "VALUES(?, ?, ?, ?)",
        (client_id, contenido, tipo, modelo_usado),
    )


def update_analysis(analysis_id: int, contenido: str) -> None:
    execute(
        "UPDATE commercial_analyses SET contenido = ? WHERE id = ?",
        (contenido, analysis_id),
    )


def delete_analysis(analysis_id: int) -> None:
    execute("DELETE FROM commercial_analyses WHERE id = ?", (analysis_id,))


def etiqueta(fila) -> str:
    """Cómo se lee una entrada en la lista del histórico."""
    fecha = (fila["fecha"] or "")[:16].replace("-", "/").replace("T", " ")
    nombre = TIPOS.get(fila["tipo"] or "manual", "Análisis")
    modelo = fila["modelo_usado"] or ""
    return f"{fecha} · {nombre}" + (f" · {modelo}" if modelo else "")
