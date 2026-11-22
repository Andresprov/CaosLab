"""Semana 7 — casos diseñados para `evaluar_estado_estable()`.

Oráculo: README, sección «Funcionalidad de la semana 5» (HU-01, criterio de
aceptación, casos límite y casos de error) y la nota de diseño ADR-002: el
umbral es **inclusivo**, estar exactamente en el límite todavía está dentro del
presupuesto. Ningún esperado de este archivo salió de ejecutar el código.

La tabla de casos está en `registro_pruebas.md`, sección 1.1. Esta es la función
que combina varias condiciones, así que su tabla de decisión está abajo.
"""

import pytest

from caoslab.estado_estable import evaluar_estado_estable
from caoslab.modelos import Estado, Muestra, PresupuestoError


def tanda(exitosas, fallidas, latencia_ms=100.0):
    return [Muestra(True, latencia_ms) for _ in range(exitosas)] + [
        Muestra(False, latencia_ms) for _ in range(fallidas)
    ]


# ---------------------------------------------------------------------------
# Tabla de decisión
#   C1: hay al menos `minimo_muestras` muestras
#   C2: tasa de error > max_tasa_error
#   C3: latencia p95 > max_latencia_p95_ms
# Cuando C1 es «no», C2 y C3 no importan: no se calcula ninguna métrica.
# ---------------------------------------------------------------------------

TABLA_DE_DECISION = [
    pytest.param(
        tanda(0, 2, 9000.0),
        PresupuestoError(0.05, 300.0, 5),
        Estado.MUESTRAS_INSUFICIENTES,
        (),
        id="R1-C1no-C2y C3 indiferentes",
    ),
    pytest.param(
        tanda(18, 2, 100.0),
        PresupuestoError(0.10, 300.0, 5),
        Estado.CONTINUAR,
        (),
        id="R2-C1si-C2no-C3no",
    ),
    pytest.param(
        tanda(17, 3, 100.0),
        PresupuestoError(0.10, 300.0, 5),
        Estado.ABORTAR,
        ("tasa de error",),
        id="R3-C1si-C2si-C3no",
    ),
    pytest.param(
        tanda(20, 0, 400.0),
        PresupuestoError(0.10, 300.0, 5),
        Estado.ABORTAR,
        ("latencia p95",),
        id="R4-C1si-C2no-C3si",
    ),
    pytest.param(
        tanda(15, 5, 400.0),
        PresupuestoError(0.10, 300.0, 5),
        Estado.ABORTAR,
        ("tasa de error", "latencia p95"),
        id="R5-C1si-C2si-C3si",
    ),
]


@pytest.mark.parametrize("muestras, presupuesto, estado, motivos", TABLA_DE_DECISION)
def test_tabla_de_decision_del_estado_estable(muestras, presupuesto, estado, motivos):
    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.estado is estado
    assert len(veredicto.motivos) == len(motivos)
    for esperado, motivo in zip(motivos, veredicto.motivos):
        assert esperado in motivo


def test_sin_evidencia_no_reporta_metricas_inventadas():
    """R1: el contrato fija tasa 0.0 y p95 0.0 cuando no hay evidencia."""
    veredicto = evaluar_estado_estable(tanda(0, 2, 9000.0), PresupuestoError(0.05, 300.0, 5))

    assert veredicto.estado is Estado.MUESTRAS_INSUFICIENTES
    assert veredicto.tasa_error == pytest.approx(0.0)
    assert veredicto.latencia_p95_ms == pytest.approx(0.0)
    assert veredicto.motivos == ()


# ---------------------------------------------------------------------------
# Valores límite de la tasa de error (umbral inclusivo, ADR-002)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exitosas, fallidas, max_tasa_error, tasa_esperada, estado",
    [
        # Último valor de la partición «dentro del presupuesto» y primero de la siguiente.
        (19, 1, 0.10, 0.05, Estado.CONTINUAR),  # por debajo del umbral
        (18, 2, 0.10, 0.10, Estado.CONTINUAR),  # justo en el umbral: sigue dentro
        (17, 3, 0.10, 0.15, Estado.ABORTAR),  # primer valor que lo supera
        # max_tasa_error = 0.0 es válido: cualquier fallo agota el presupuesto.
        (10, 0, 0.00, 0.00, Estado.CONTINUAR),
        (9, 1, 0.00, 0.10, Estado.ABORTAR),
        # max_tasa_error = 1.0: ni con todas las peticiones fallidas se aborta por tasa.
        (0, 20, 1.00, 1.00, Estado.CONTINUAR),
    ],
)
def test_limites_de_la_tasa_de_error(exitosas, fallidas, max_tasa_error, tasa_esperada, estado):
    presupuesto = PresupuestoError(max_tasa_error, 300.0, minimo_muestras=1)

    veredicto = evaluar_estado_estable(tanda(exitosas, fallidas, 100.0), presupuesto)

    assert veredicto.tasa_error == pytest.approx(tasa_esperada)
    assert veredicto.estado is estado


# ---------------------------------------------------------------------------
# Valores límite de la latencia p95 (umbral inclusivo, ADR-002)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "latencia_ms, max_latencia_p95_ms, estado",
    [
        (299.9, 300.0, Estado.CONTINUAR),  # último valor dentro del presupuesto
        (300.0, 300.0, Estado.CONTINUAR),  # justo en el umbral: sigue dentro
        (300.1, 300.0, Estado.ABORTAR),  # primer valor que lo supera
        (0.0, 300.0, Estado.CONTINUAR),  # latencia cero: válida, es el borde inferior
    ],
)
def test_limites_de_la_latencia_p95(latencia_ms, max_latencia_p95_ms, estado):
    presupuesto = PresupuestoError(0.05, max_latencia_p95_ms, minimo_muestras=1)

    veredicto = evaluar_estado_estable(tanda(10, 0, latencia_ms), presupuesto)

    assert veredicto.latencia_p95_ms == pytest.approx(latencia_ms)
    assert veredicto.estado is estado


# ---------------------------------------------------------------------------
# Valores límite del mínimo de muestras
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cantidad, minimo_muestras, estado",
    [
        (0, 1, Estado.MUESTRAS_INSUFICIENTES),  # lista vacía con el mínimo más bajo
        (1, 1, Estado.CONTINUAR),  # exactamente el mínimo
        (4, 5, Estado.MUESTRAS_INSUFICIENTES),  # una muestra menos que el mínimo
        (5, 5, Estado.CONTINUAR),  # exactamente el mínimo
        (6, 5, Estado.CONTINUAR),  # una más que el mínimo
    ],
)
def test_limites_del_minimo_de_muestras(cantidad, minimo_muestras, estado):
    presupuesto = PresupuestoError(0.05, 300.0, minimo_muestras=minimo_muestras)

    veredicto = evaluar_estado_estable(tanda(cantidad, 0, 100.0), presupuesto)

    assert veredicto.estado is estado


# ---------------------------------------------------------------------------
# Percentil 95 por rango más cercano: indice = ceil(0.95 * n) - 1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cantidad, p95_esperado",
    [
        (1, 1.0),  # ceil(0.95) - 1 = 0 -> la única muestra
        (2, 2.0),  # ceil(1.90) - 1 = 1 -> la más lenta de dos
        (10, 10.0),  # ceil(9.50) - 1 = 9 -> la más lenta de diez
        (19, 19.0),  # ceil(18.05) - 1 = 18 -> la más lenta de diecinueve
        (20, 19.0),  # ceil(19.00) - 1 = 18 -> la penúltima: el pico queda afuera
        (21, 20.0),  # ceil(19.95) - 1 = 19 -> la penúltima
        (40, 38.0),  # ceil(38.00) - 1 = 37 -> la antepenúltima
    ],
)
def test_el_p95_es_una_latencia_realmente_observada(cantidad, p95_esperado):
    """Latencias 1.0, 2.0, ... n.0 en orden descendente para que el orden no ayude."""
    muestras = [Muestra(True, float(valor)) for valor in range(cantidad, 0, -1)]
    presupuesto = PresupuestoError(0.05, 1_000_000.0, minimo_muestras=1)

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.latencia_p95_ms == pytest.approx(p95_esperado)


# ---------------------------------------------------------------------------
# Particiones inválidas: cada una lanza ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "presupuesto, mensaje",
    [
        (PresupuestoError(-0.01, 300.0), "max_tasa_error"),  # primer valor por debajo de 0.0
        (PresupuestoError(1.01, 300.0), "max_tasa_error"),  # primer valor por encima de 1.0
        (PresupuestoError(1.50, 300.0), "max_tasa_error"),  # partición inválida alta
        (PresupuestoError(0.05, 0.0), "max_latencia_p95_ms"),  # el borde 0 no es válido
        (PresupuestoError(0.05, -5.0), "max_latencia_p95_ms"),  # partición negativa
        (PresupuestoError(0.05, 300.0, 0), "minimo_muestras"),  # último valor inválido
        (PresupuestoError(0.05, 300.0, -3), "minimo_muestras"),  # partición negativa
    ],
)
def test_presupuesto_invalido_lanza_value_error(presupuesto, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        evaluar_estado_estable(tanda(10, 0, 100.0), presupuesto)


@pytest.mark.parametrize(
    "presupuesto",
    [
        PresupuestoError(0.0, 0.1, 1),  # todos los bordes válidos a la vez
        PresupuestoError(1.0, 300.0, 1),
    ],
)
def test_los_bordes_validos_del_presupuesto_no_lanzan(presupuesto):
    veredicto = evaluar_estado_estable(tanda(10, 0, 0.05), presupuesto)

    assert veredicto.estado in (Estado.CONTINUAR, Estado.ABORTAR)


@pytest.mark.parametrize(
    "latencia_ms, posicion",
    [
        (-0.1, 3),  # primer valor por debajo del borde válido
        (-1000.0, 3),  # partición negativa clara
    ],
)
def test_latencia_negativa_lanza_value_error_nombrando_la_muestra(latencia_ms, posicion):
    muestras = tanda(3, 0, 100.0) + [Muestra(True, latencia_ms)]

    with pytest.raises(ValueError, match=f"la muestra {posicion} tiene una latencia negativa"):
        evaluar_estado_estable(muestras, PresupuestoError(0.05, 300.0))


def test_latencia_cero_es_valida_y_no_lanza():
    """0.0 es el último valor válido de la partición de latencias."""
    veredicto = evaluar_estado_estable(
        [Muestra(True, 0.0)], PresupuestoError(0.05, 300.0, minimo_muestras=1)
    )

    assert veredicto.latencia_p95_ms == pytest.approx(0.0)
    assert veredicto.estado is Estado.CONTINUAR


# ---------------------------------------------------------------------------
# Volumen y pureza (datos sintéticos del conftest)
# ---------------------------------------------------------------------------


def test_volumen_de_trescientas_muestras_con_un_pico_aislado(tanda_de_volumen):
    """301 muestras: tasa 15/301 y el pico de 9000 ms queda sobre el percentil."""
    presupuesto = PresupuestoError(0.06, 300.0, minimo_muestras=10)

    veredicto = evaluar_estado_estable(tanda_de_volumen, presupuesto)

    assert veredicto.tasa_error == pytest.approx(15 / 301)
    assert veredicto.latencia_p95_ms == pytest.approx(80.0)
    assert veredicto.estado is Estado.CONTINUAR


def test_la_funcion_no_muta_las_muestras_que_recibe():
    """El contrato dice que la función es pura: ordena una copia, no la entrada."""
    muestras = [Muestra(True, 500.0), Muestra(True, 100.0), Muestra(False, 300.0)]
    original = list(muestras)

    evaluar_estado_estable(muestras, PresupuestoError(0.5, 1000.0))

    assert muestras == original
