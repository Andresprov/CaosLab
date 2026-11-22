"""Semana 7 — casos diseñados para `ejecutar_experimento()`.

Oráculo: README, sección «Cómo decide el motor» (los cinco pasos) y
«Reversión garantizada». Es la segunda función que combina condiciones, así que
abajo está su tabla de decisión. Tabla de casos en `registro_pruebas.md`,
sección 1.3.
"""

import signal

import pytest

from caoslab.modelos import Estado
from caoslab.motor import Conclusion, ejecutar_experimento
from tests.falsos import (
    InyectorFalso,
    SondaFalsa,
    experimento_de_prueba,
    fallidas,
    sanas,
    sin_esperar,
)


def correr(tandas, al_recoger=None, **cambios):
    inyector = InyectorFalso()
    sonda = SondaFalsa(tandas, al_recoger=al_recoger)
    resultado = ejecutar_experimento(
        experimento_de_prueba(**cambios), inyector, sonda, dormir=sin_esperar
    )
    return resultado, inyector, sonda


def ctrl_c():
    signal.raise_signal(signal.SIGINT)


# ---------------------------------------------------------------------------
# Tabla de decisión de la conclusión del experimento
#   C1: la línea base dio CONTINUAR
#   C2: llegó una señal de parada
#   C3: alguna ventana dio ABORTAR
#   C4: todas las ventanas dieron MUESTRAS_INSUFICIENTES
# Cuando C1 es «no» las otras tres no importan: no se inyecta nada.
# El experimento por omisión dura 15 s en ventanas de 5 s, es decir 3 ventanas.
# ---------------------------------------------------------------------------

TABLA_DE_DECISION = [
    pytest.param(
        [fallidas(10)] + [sanas()] * 3,
        None,
        Conclusion.LINEA_BASE_INESTABLE,
        [],
        0,
        id="R1-C1no-por-presupuesto-agotado",
    ),
    pytest.param(
        [sanas(2)] + [sanas()] * 3,
        None,
        Conclusion.LINEA_BASE_INESTABLE,
        [],
        0,
        id="R2-C1no-por-falta-de-muestras",
    ),
    pytest.param(
        [sanas()] * 5,
        {2: ctrl_c},
        Conclusion.INTERRUMPIDO,
        ["inyectar", "revertir"],
        0,
        id="R3-C1si-C2si",
    ),
    pytest.param(
        [sanas(), sanas(), fallidas(), sanas()],
        None,
        Conclusion.ABORTADO,
        ["inyectar", "revertir"],
        2,
        id="R4-C1si-C2no-C3si",
    ),
    pytest.param(
        [sanas(), [], [], []],
        None,
        Conclusion.SIN_EVIDENCIA,
        ["inyectar", "revertir"],
        3,
        id="R5-C1si-C2no-C3no-C4si",
    ),
    pytest.param(
        [sanas()] * 4,
        None,
        Conclusion.SUPERADO,
        ["inyectar", "revertir"],
        3,
        id="R6-C1si-C2no-C3no-C4no",
    ),
]


@pytest.mark.parametrize(
    "tandas, al_recoger, conclusion, eventos, cantidad_de_ventanas", TABLA_DE_DECISION
)
def test_tabla_de_decision_de_la_conclusion(
    tandas, al_recoger, conclusion, eventos, cantidad_de_ventanas
):
    resultado, inyector, sonda = correr(tandas, al_recoger=al_recoger)

    assert resultado.conclusion is conclusion
    assert inyector.eventos == eventos
    assert len(resultado.ventanas) == cantidad_de_ventanas
    assert sonda.detenida is True


def test_una_ventana_sin_evidencia_entre_ventanas_sanas_no_impide_superar():
    """Partición mixta: la regla 4 solo da SIN_EVIDENCIA si ninguna juntó muestras."""
    resultado, _, _ = correr([sanas(), sanas(), sanas(2), sanas()])

    assert [ventana.veredicto.estado for ventana in resultado.ventanas] == [
        Estado.CONTINUAR,
        Estado.MUESTRAS_INSUFICIENTES,
        Estado.CONTINUAR,
    ]
    assert resultado.conclusion is Conclusion.SUPERADO


def test_aborta_en_la_primera_ventana_mala_y_deja_de_medir():
    """La regla 3 detiene el experimento: la tercera ventana no se llega a medir."""
    resultado, _, sonda = correr([sanas(), fallidas(), sanas(), sanas()])

    assert resultado.conclusion is Conclusion.ABORTADO
    assert len(resultado.ventanas) == 1
    assert sonda.recogidas == 2  # la línea base y una sola ventana
    assert resultado.ventanas[-1].veredicto.motivos


def test_no_se_inyecta_nada_cuando_la_linea_base_esta_inestable():
    """Si no se inyectó, no hay nada que revertir: el inyector no se toca."""
    resultado, inyector, _ = correr([fallidas(10)] + [sanas()] * 3)

    assert resultado.fallo_inyectado is False
    assert inyector.eventos == []


# ---------------------------------------------------------------------------
# Valores límite del número de ventanas: ceil(duracion_s / ventana_s)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "duracion_s, ventana_s, ventanas_esperadas",
    [
        (1, 5, 1),  # ceil(0.2) = 1: una duración más corta que la ventana igual mide una
        (5, 5, 1),  # ceil(1.0) = 1: el borde exacto no agrega una ventana de sobra
        (6, 5, 2),  # ceil(1.2) = 2: el primer valor que sí la agrega
        (10, 5, 2),  # ceil(2.0) = 2
        (11, 5, 3),  # ceil(2.2) = 3
        (30, 5, 6),  # el experimento del README
    ],
)
def test_limites_del_numero_de_ventanas(duracion_s, ventana_s, ventanas_esperadas):
    resultado, _, _ = correr(
        [sanas()] * (ventanas_esperadas + 1), duracion_s=duracion_s, ventana_s=ventana_s
    )

    assert len(resultado.ventanas) == ventanas_esperadas
    assert resultado.conclusion is Conclusion.SUPERADO


@pytest.mark.parametrize(
    "duracion_s, ventana_s, esperas",
    [
        (10, 5, [10, 5, 5]),  # primero la línea base, después cada ventana
        (5, 5, [10, 5]),
    ],
)
def test_espera_la_linea_base_y_despues_cada_ventana(duracion_s, ventana_s, esperas):
    medidas = []

    ejecutar_experimento(
        experimento_de_prueba(duracion_s=duracion_s, ventana_s=ventana_s),
        InyectorFalso(),
        SondaFalsa([sanas()] * 4),
        dormir=medidas.append,
    )

    assert medidas == esperas


# ---------------------------------------------------------------------------
# Reversión garantizada: pase lo que pase, se revierte
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "excepcion",
    [
        RuntimeError("se cayó la sonda"),
        KeyboardInterrupt(),
        MemoryError(),
    ],
)
def test_revierte_el_fallo_aunque_salte_cualquier_excepcion(excepcion):
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas(), sanas()], al_recoger={2: lambda: (_ for _ in ()).throw(excepcion)})

    with pytest.raises(type(excepcion)):
        ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida is True


def test_revierte_aunque_la_inyeccion_misma_falle():
    inyector = InyectorFalso(falla_al_inyectar=True)
    sonda = SondaFalsa([sanas()] * 4)

    with pytest.raises(RuntimeError, match="no se pudo inyectar"):
        ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
