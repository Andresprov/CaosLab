from dataclasses import dataclass
from enum import Enum


class Estado(str, Enum):
    """Resultado de evaluar una ventana: CONTINUAR, ABORTAR o MUESTRAS_INSUFICIENTES."""
    CONTINUAR = "CONTINUAR"
    ABORTAR = "ABORTAR"
    MUESTRAS_INSUFICIENTES = "MUESTRAS_INSUFICIENTES"


@dataclass(frozen=True)
class Muestra:
    """Una petición de la sonda: si salió bien y cuánto tardó en milisegundos."""
    exitosa: bool
    latencia_ms: float


@dataclass(frozen=True)
class PresupuestoError:
    """Límites aceptados antes de inyectar el fallo."""
    max_tasa_error: float
    max_latencia_p95_ms: float
    minimo_muestras: int = 1


@dataclass(frozen=True)
class Veredicto:
    """Respuesta de evaluar_estado_estable(): estado, métricas y motivos para abortar."""
    estado: Estado
    tasa_error: float
    latencia_p95_ms: float
    motivos: tuple[str, ...] = ()
