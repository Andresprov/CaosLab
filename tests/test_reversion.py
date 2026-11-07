import signal

import pytest

from caoslab.motor import Conclusion, ejecutar_experimento
from tests.falsos import InyectorFalso, SondaFalsa, experimento_de_prueba, sanas, sin_esperar


def lanzar(excepcion):
    def accion():
        raise excepcion

    return accion


def ctrl_c():
    signal.raise_signal(signal.SIGINT)


def test_revierte_si_la_sonda_falla_a_mitad_del_experimento():
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas(), sanas()], al_recoger={2: lanzar(RuntimeError("se cayó la sonda"))})

    with pytest.raises(RuntimeError, match="se cayó la sonda"):
        ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida


def test_revierte_si_llega_un_keyboardinterrupt():
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas(), sanas()], al_recoger={2: lanzar(KeyboardInterrupt())})

    with pytest.raises(KeyboardInterrupt):
        ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida


def test_ctrl_c_durante_el_fallo_detiene_el_experimento_y_revierte():
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas()] * 4, al_recoger={2: ctrl_c})

    resultado = ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert resultado.conclusion is Conclusion.INTERRUMPIDO
    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida


def test_ctrl_c_durante_la_linea_base_no_llega_a_inyectar():
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas()] * 4, al_recoger={1: ctrl_c})

    resultado = ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert resultado.conclusion is Conclusion.INTERRUMPIDO
    assert inyector.eventos == []
    assert sonda.detenida


def test_intenta_revertir_aunque_falle_la_inyeccion():
    inyector = InyectorFalso(falla_al_inyectar=True)
    sonda = SondaFalsa([sanas()] * 4)

    with pytest.raises(RuntimeError, match="no se pudo inyectar"):
        ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida


def test_revierte_al_terminar_normalmente():
    inyector = InyectorFalso()
    sonda = SondaFalsa([sanas()] * 4)

    ejecutar_experimento(experimento_de_prueba(), inyector, sonda, dormir=sin_esperar)

    assert inyector.eventos == ["inyectar", "revertir"]
    assert sonda.detenida


def test_deja_el_manejador_de_ctrl_c_como_estaba():
    antes = signal.getsignal(signal.SIGINT)

    ejecutar_experimento(experimento_de_prueba(), InyectorFalso(), SondaFalsa([sanas()] * 4), dormir=sin_esperar)

    assert signal.getsignal(signal.SIGINT) is antes
