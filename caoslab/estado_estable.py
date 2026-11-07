"""Evaluación del estado estable de un experimento de caos (HU-01)."""

import math
from collections.abc import Sequence

from caoslab.modelos import Estado, Muestra, PresupuestoError, Veredicto


def evaluar_estado_estable(
    muestras: Sequence[Muestra],
    presupuesto: PresupuestoError,
) -> Veredicto:
    """Decide si el experimento sigue dentro del presupuesto de error."""
    if not 0.0 <= presupuesto.max_tasa_error <= 1.0:
        raise ValueError(
            f"max_tasa_error debe estar entre 0.0 y 1.0: "
            f"{presupuesto.max_tasa_error}"
        )
    if presupuesto.max_latencia_p95_ms <= 0:
        raise ValueError(
            f"max_latencia_p95_ms debe ser mayor que 0: "
            f"{presupuesto.max_latencia_p95_ms}"
        )
    if presupuesto.minimo_muestras < 1:
        raise ValueError(
            f"minimo_muestras debe ser al menos 1: {presupuesto.minimo_muestras}"
        )

    for posicion, muestra in enumerate(muestras):
        if muestra.latencia_ms < 0:
            raise ValueError(
                f"la muestra {posicion} tiene una latencia negativa: "
                f"{muestra.latencia_ms} ms"
            )

    if len(muestras) < presupuesto.minimo_muestras:
        return Veredicto(
            estado=Estado.MUESTRAS_INSUFICIENTES,
            tasa_error=0.0,
            latencia_p95_ms=0.0,
            motivos=(),
        )

    fallidas = sum(1 for muestra in muestras if not muestra.exitosa)
    tasa_error = fallidas / len(muestras)

    # Percentil 95 por el metodo de rango mas cercano: indice = ceil(0.95*n) - 1.
    # Con int(0.95*n) y n = 20 el indice daba 19 (la ultima muestra) en vez de
    # 18, asi que un unico pico aislado se tomaba como el p95.
    latencias = sorted(muestra.latencia_ms for muestra in muestras)
    indice = math.ceil(0.95 * len(latencias)) - 1
    latencia_p95 = latencias[indice]

    motivos = []
    if tasa_error > presupuesto.max_tasa_error:
        motivos.append(
            f"tasa de error {tasa_error:.2%} supera el máximo de "
            f"{presupuesto.max_tasa_error:.2%}"
        )
    if latencia_p95 > presupuesto.max_latencia_p95_ms:
        motivos.append(
            f"latencia p95 {latencia_p95:.1f} ms supera el máximo de "
            f"{presupuesto.max_latencia_p95_ms:.1f} ms"
        )

    estado = Estado.ABORTAR if motivos else Estado.CONTINUAR
    return Veredicto(
        estado=estado,
        tasa_error=tasa_error,
        latencia_p95_ms=latencia_p95,
        motivos=tuple(motivos),
    )
