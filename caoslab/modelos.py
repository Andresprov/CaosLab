from dataclasses import dataclass
from enum import Enum


class Estado(str, Enum):
    CONTINUAR = "CONTINUAR"
    ABORTAR = "ABORTAR"
    MUESTRAS_INSUFICIENTES = "MUESTRAS_INSUFICIENTES"


@dataclass(frozen=True)
class Muestra:
    exitosa: bool
    latencia_ms: float


@dataclass(frozen=True)
class PresupuestoError:
    max_tasa_error: float
    max_latencia_p95_ms: float
    minimo_muestras: int = 1


@dataclass(frozen=True)
class Veredicto:
    estado: Estado
    tasa_error: float
    latencia_p95_ms: float
    motivos: tuple[str, ...] = ()
