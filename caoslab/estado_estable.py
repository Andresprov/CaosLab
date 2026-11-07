import math
from collections.abc import Sequence

from caoslab.modelos import Estado, Muestra, PresupuestoError, Veredicto

PERCENTIL_LATENCIA = 0.95
SIN_EVIDENCIA = 0.0


def evaluar_estado_estable(
    muestras: Sequence[Muestra],
    presupuesto: PresupuestoError,
) -> Veredicto:
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


def _validar_presupuesto(presupuesto: PresupuestoError) -> None:
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
    for posicion, muestra in enumerate(muestras):
        if muestra.latencia_ms < 0:
            raise ValueError(
                f"la muestra {posicion} tiene una latencia negativa: "
                f"{muestra.latencia_ms} ms"
            )


def _tasa_de_error(muestras: Sequence[Muestra]) -> float:
    fallidas = sum(1 for muestra in muestras if not muestra.exitosa)
    return fallidas / len(muestras)


def _percentil_por_rango_mas_cercano(
    valores: Sequence[float], percentil: float
) -> float:
    ordenados = sorted(valores)
    indice = math.ceil(percentil * len(ordenados)) - 1
    return ordenados[indice]


def _veredicto_sin_evidencia() -> Veredicto:
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
