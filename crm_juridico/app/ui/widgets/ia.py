"""Ejecutar llamadas a la IA sin congelar la interfaz.

Una consulta a la IA tarda de unos segundos a más de un minuto según el
modelo. Hecha en el hilo de la ventana, Windows y macOS la pintan en gris y
la dan por colgada. Por eso va aparte.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from app.services.ai_provider import IAError


class TrabajoIA(QObject):
    """Envuelve una función de `ai_agent` para correrla en otro hilo."""

    terminado = pyqtSignal(object)   # RespuestaIA
    fallido = pyqtSignal(str)

    def __init__(self, funcion, *args, **kwargs):
        super().__init__()
        self._funcion, self._args, self._kwargs = funcion, args, kwargs

    def run(self):
        try:
            self.terminado.emit(self._funcion(*self._args, **self._kwargs))
        except IAError as e:
            self.fallido.emit(str(e))
        except Exception as e:                      # noqa: BLE001
            self.fallido.emit(f"Error inesperado: {e}")
