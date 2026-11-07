"""Pruebas de HU-01: detener el experimento cuando se agota el presupuesto.

Escritas antes de la implementación. El contrato que comprueban está en el
README, en la sección «Funcionalidad de la semana 5».

Organización:
  - Casos normales: 3
  - Casos límite:   6
  - Casos de error: 3
"""

import pytest

from caoslab.estado_estable import evaluar_estado_estable
from caoslab.modelos import Estado, Muestra, PresupuestoError


def muestras_sanas(cantidad: int, latencia_ms: float = 100.0) -> list[Muestra]:
    """Atajo de lectura: `cantidad` muestras exitosas con la misma latencia."""
    return [Muestra(exitosa=True, latencia_ms=latencia_ms) for _ in range(cantidad)]


# --------------------------------------------------------------------------
# Casos normales
# --------------------------------------------------------------------------


def test_continua_cuando_todas_las_peticiones_responden_dentro_del_umbral():
    presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras_sanas(10, 120.0), presupuesto)

    assert veredicto.estado is Estado.CONTINUAR
    assert veredicto.tasa_error == 0.0
    assert veredicto.latencia_p95_ms == 120.0
    assert veredicto.motivos == ()


def test_aborta_e_indica_el_motivo_cuando_la_tasa_de_error_supera_el_presupuesto():
    muestras = [Muestra(exitosa=False, latencia_ms=90.0) for _ in range(3)]
    muestras += muestras_sanas(7, 90.0)
    presupuesto = PresupuestoError(max_tasa_error=0.10, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.estado is Estado.ABORTAR
    assert veredicto.tasa_error == pytest.approx(0.3)
    assert len(veredicto.motivos) == 1
    assert "tasa de error" in veredicto.motivos[0]


def test_aborta_con_los_dos_motivos_cuando_fallan_tasa_de_error_y_latencia():
    muestras = [Muestra(exitosa=False, latencia_ms=900.0) for _ in range(5)]
    muestras += muestras_sanas(5, 900.0)
    presupuesto = PresupuestoError(max_tasa_error=0.10, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.estado is Estado.ABORTAR
    assert len(veredicto.motivos) == 2


# --------------------------------------------------------------------------
# Casos límite
# --------------------------------------------------------------------------


def test_continua_cuando_la_tasa_de_error_es_exactamente_el_umbral():
    """El umbral es inclusivo (ADR-002): estar en el límite todavía está dentro."""
    muestras = [Muestra(exitosa=False, latencia_ms=80.0) for _ in range(2)]
    muestras += muestras_sanas(8, 80.0)
    presupuesto = PresupuestoError(max_tasa_error=0.20, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.estado is Estado.CONTINUAR
    assert veredicto.tasa_error == pytest.approx(0.20)


def test_continua_cuando_la_latencia_p95_es_exactamente_el_umbral():
    presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=250.0)

    veredicto = evaluar_estado_estable(muestras_sanas(10, 250.0), presupuesto)

    assert veredicto.estado is Estado.CONTINUAR
    assert veredicto.latencia_p95_ms == 250.0


def test_lista_vacia_devuelve_muestras_insuficientes_y_no_aborta():
    """Sin evidencia no se toma una decisión destructiva."""
    presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable([], presupuesto)

    assert veredicto.estado is Estado.MUESTRAS_INSUFICIENTES
    assert veredicto.tasa_error == 0.0
    assert veredicto.latencia_p95_ms == 0.0
    assert veredicto.motivos == ()


def test_una_sola_muestra_usa_su_propia_latencia_como_p95():
    presupuesto = PresupuestoError(max_tasa_error=0.50, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras_sanas(1, 120.0), presupuesto)

    assert veredicto.estado is Estado.CONTINUAR
    assert veredicto.latencia_p95_ms == 120.0


def test_no_aborta_cuando_hay_menos_muestras_que_el_minimo_exigido():
    """Dos fallos de dos muestras no bastan si el mínimo configurado es cinco."""
    muestras = [Muestra(exitosa=False, latencia_ms=90.0) for _ in range(2)]
    presupuesto = PresupuestoError(
        max_tasa_error=0.05, max_latencia_p95_ms=300.0, minimo_muestras=5
    )

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.estado is Estado.MUESTRAS_INSUFICIENTES


def test_un_pico_aislado_de_latencia_en_veinte_muestras_no_mueve_el_p95():
    """El p95 de 20 muestras es la posición 19 de 20 ordenadas, no la última.

    Con el método de rango más cercano: ceil(0.95 * 20) - 1 = 18, es decir
    la muestra 19 de 20. Un único pico queda por encima del percentil y no
    debe abortar el experimento.
    """
    muestras = muestras_sanas(19, 100.0) + [Muestra(exitosa=True, latencia_ms=5000.0)]
    presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=300.0)

    veredicto = evaluar_estado_estable(muestras, presupuesto)

    assert veredicto.latencia_p95_ms == 100.0
    assert veredicto.estado is Estado.CONTINUAR


# --------------------------------------------------------------------------
# Casos de error
# --------------------------------------------------------------------------


def test_latencia_negativa_lanza_valueerror_indicando_la_muestra():
    muestras = muestras_sanas(3) + [Muestra(exitosa=True, latencia_ms=-1.0)]
    presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=300.0)

    with pytest.raises(ValueError, match="latencia negativa"):
        evaluar_estado_estable(muestras, presupuesto)


def test_tasa_de_error_maxima_fuera_del_rango_cero_uno_lanza_valueerror():
    presupuesto = PresupuestoError(max_tasa_error=1.5, max_latencia_p95_ms=300.0)

    with pytest.raises(ValueError, match="max_tasa_error"):
        evaluar_estado_estable(muestras_sanas(3), presupuesto)


def test_minimo_de_muestras_menor_que_uno_lanza_valueerror():
    presupuesto = PresupuestoError(
        max_tasa_error=0.05, max_latencia_p95_ms=300.0, minimo_muestras=0
    )

    with pytest.raises(ValueError, match="minimo_muestras"):
        evaluar_estado_estable(muestras_sanas(3), presupuesto)
