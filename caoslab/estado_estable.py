"""Evaluación del estado estable de un experimento de caos (HU-01).

`evaluar_estado_estable()` es el punto de entrada: recibe las muestras de una
ventana de observación y el presupuesto de error acordado, y responde si el
experimento puede seguir corriendo o hay que abortarlo.

La función es pura: no lee el reloj, no escribe en disco, no toca la red y no
muta las muestras que recibe. Por eso se puede probar sin levantar Docker.
"""

import math
from collections.abc import Sequence

from caoslab.modelos import Estado, Muestra, PresupuestoError, Veredicto

#: Percentil de latencia que vigila el experimento, como fracción.
PERCENTIL_LATENCIA = 0.95

#: Valores que reporta un veredicto cuando todavía no hay evidencia.
SIN_EVIDENCIA = 0.0


def evaluar_estado_estable(
    muestras: Sequence[Muestra],
    presupuesto: PresupuestoError,
) -> Veredicto:
    """Decide si el experimento sigue dentro del presupuesto de error.

    Args:
        muestras: observaciones de la ventana actual, en cualquier orden.
        presupuesto: límites que el equipo aceptó antes de inyectar el fallo.

    Returns:
        Un `Veredicto` con el estado, las métricas calculadas y, si hay que
        abortar, el motivo de cada umbral superado.

    Raises:
        ValueError: si el presupuesto está fuera de rango o alguna muestra
            tiene una latencia negativa.
    """
    _validar_presupuesto(presupuesto)
    _validar_muestras(muestras)

    if len(muestras) < presupuesto.minimo_muestras:
        return _veredicto_sin_evidencia()

    tasa_error = _tasa_de_error(muestras)
    latencia_p95 = _percentil_por_rango_mas_cercano(
        [muestra.latencia_ms for muestra in muestras], PERCENTIL_LATENCIA
    )
    motivos = _motivos_para_abortar(tasa_error, latencia_p95, presupuesto)

    return Veredicto(
        estado=Estado.ABORTAR if motivos else Estado.CONTINUAR,
        tasa_error=tasa_error,
        latencia_p95_ms=latencia_p95,
        motivos=motivos,
    )


# --------------------------------------------------------------------------
# Validación
# --------------------------------------------------------------------------


def _validar_presupuesto(presupuesto: PresupuestoError) -> None:
    """Rechaza un presupuesto que no se puede comparar contra nada."""
    if not 0.0 <= presupuesto.max_tasa_error <= 1.0:
        raise ValueError(
            "max_tasa_error debe estar entre 0.0 y 1.0: "
            f"{presupuesto.max_tasa_error}"
        )
    if presupuesto.max_latencia_p95_ms <= 0:
        raise ValueError(
            "max_latencia_p95_ms debe ser mayor que 0: "
            f"{presupuesto.max_latencia_p95_ms}"
        )
    if presupuesto.minimo_muestras < 1:
        raise ValueError(
            f"minimo_muestras debe ser al menos 1: {presupuesto.minimo_muestras}"
        )


def _validar_muestras(muestras: Sequence[Muestra]) -> None:
    """Una latencia negativa es un error del recolector, no un dato del sistema."""
    for posicion, muestra in enumerate(muestras):
        if muestra.latencia_ms < 0:
            raise ValueError(
                f"la muestra {posicion} tiene una latencia negativa: "
                f"{muestra.latencia_ms} ms"
            )


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------


def _tasa_de_error(muestras: Sequence[Muestra]) -> float:
    """Fracción de muestras que no respondieron correctamente."""
    fallidas = sum(1 for muestra in muestras if not muestra.exitosa)
    return fallidas / len(muestras)


def _percentil_por_rango_mas_cercano(
    valores: Sequence[float], percentil: float
) -> float:
    """Percentil sin interpolar: devuelve siempre un valor observado.

    Índice = ceil(percentil * n) - 1 sobre los valores ordenados. Con 20
    valores y el percentil 95 el índice es 18, es decir la posición 19 de 20:
    un único pico aislado queda por encima del percentil y no lo mueve.
    """
    ordenados = sorted(valores)
    indice = math.ceil(percentil * len(ordenados)) - 1
    return ordenados[indice]


# --------------------------------------------------------------------------
# Veredicto
# --------------------------------------------------------------------------


def _veredicto_sin_evidencia() -> Veredicto:
    """Sin muestras suficientes no se toma una decisión destructiva."""
    return Veredicto(
        estado=Estado.MUESTRAS_INSUFICIENTES,
        tasa_error=SIN_EVIDENCIA,
        latencia_p95_ms=SIN_EVIDENCIA,
        motivos=(),
    )


def _motivos_para_abortar(
    tasa_error: float,
    latencia_p95_ms: float,
    presupuesto: PresupuestoError,
) -> tuple[str, ...]:
    """Lista todos los umbrales superados, no solo el primero.

    Los umbrales son inclusivos (ADR-002): estar exactamente en el límite
    todavía está dentro del presupuesto, solo se aborta al superarlo.
    """
    motivos: list[str] = []

    if tasa_error > presupuesto.max_tasa_error:
        motivos.append(
            f"tasa de error {tasa_error:.2%} supera el máximo de "
            f"{presupuesto.max_tasa_error:.2%}"
        )
    if latencia_p95_ms > presupuesto.max_latencia_p95_ms:
        motivos.append(
            f"latencia p95 {latencia_p95_ms:.1f} ms supera el máximo de "
            f"{presupuesto.max_latencia_p95_ms:.1f} ms"
        )

    return tuple(motivos)
