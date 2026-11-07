"""Modelos del dominio de un experimento de caos.

Los tres son `frozen=True` para que un veredicto ya emitido no se pueda
modificar después: una decisión de abortar un experimento debe quedar como
un registro inmutable de lo que se observó.
"""

from dataclasses import dataclass
from enum import Enum


class Estado(str, Enum):
    """Resultado de evaluar el estado estable durante un experimento."""

    CONTINUAR = "CONTINUAR"
    ABORTAR = "ABORTAR"
    MUESTRAS_INSUFICIENTES = "MUESTRAS_INSUFICIENTES"


@dataclass(frozen=True)
class Muestra:
    """Una observación tomada mientras el fallo está inyectado.

    exitosa: True si la petición respondió correctamente.
    latencia_ms: latencia observada en milisegundos; no puede ser negativa.
    """

    exitosa: bool
    latencia_ms: float


@dataclass(frozen=True)
class PresupuestoError:
    """Límites que el equipo aceptó antes de inyectar el fallo.

    max_tasa_error: fracción de error tolerada, entre 0.0 y 1.0.
    max_latencia_p95_ms: latencia p95 tolerada, en milisegundos.
    minimo_muestras: muestras mínimas para emitir un veredicto.
    """

    max_tasa_error: float
    max_latencia_p95_ms: float
    minimo_muestras: int = 1


@dataclass(frozen=True)
class Veredicto:
    """Decisión sobre si el experimento puede seguir corriendo."""

    estado: Estado
    tasa_error: float
    latencia_p95_ms: float
    motivos: tuple[str, ...] = ()
