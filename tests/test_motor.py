from caoslab.modelos import Estado
from caoslab.motor import Conclusion, ejecutar_experimento
from tests.falsos import InyectorFalso, SondaFalsa, experimento_de_prueba, fallidas, sanas, sin_esperar


def correr(tandas, **cambios):
    inyector = InyectorFalso()
    sonda = SondaFalsa(tandas)
    resultado = ejecutar_experimento(experimento_de_prueba(**cambios), inyector, sonda, dormir=sin_esperar)
    return resultado, inyector, sonda


def test_si_el_sistema_aguanta_todas_las_ventanas_el_experimento_se_supera():
    resultado, inyector, _ = correr([sanas(), sanas(), sanas(), sanas()])

    assert resultado.conclusion is Conclusion.SUPERADO
    assert resultado.linea_base.estado is Estado.CONTINUAR
    assert [v.veredicto.estado for v in resultado.ventanas] == [Estado.CONTINUAR] * 3
    assert inyector.eventos == ["inyectar", "revertir"]


def test_aborta_en_la_primera_ventana_que_agota_el_presupuesto_y_no_sigue_midiendo():
    resultado, inyector, sonda = correr([sanas(), sanas(), fallidas(), sanas()])

    assert resultado.conclusion is Conclusion.ABORTADO
    assert len(resultado.ventanas) == 2
    assert resultado.ventanas[-1].veredicto.estado is Estado.ABORTAR
    assert resultado.ventanas[-1].veredicto.motivos
    assert sonda.recogidas == 3
    assert inyector.eventos == ["inyectar", "revertir"]


def test_no_inyecta_si_la_linea_base_ya_esta_fuera_del_presupuesto():
    resultado, inyector, _ = correr([fallidas(), sanas(), sanas(), sanas()])

    assert resultado.conclusion is Conclusion.LINEA_BASE_INESTABLE
    assert resultado.linea_base.estado is Estado.ABORTAR
    assert resultado.ventanas == []
    assert inyector.eventos == []


def test_no_inyecta_si_la_linea_base_no_junto_muestras_suficientes():
    resultado, inyector, _ = correr([sanas(2), sanas(), sanas(), sanas()])

    assert resultado.conclusion is Conclusion.LINEA_BASE_INESTABLE
    assert resultado.linea_base.estado is Estado.MUESTRAS_INSUFICIENTES
    assert inyector.eventos == []


def test_una_ventana_sin_muestras_suficientes_no_aborta_el_experimento():
    resultado, _, _ = correr([sanas(), sanas(), fallidas(2), sanas()])

    assert resultado.conclusion is Conclusion.SUPERADO
    assert [v.veredicto.estado for v in resultado.ventanas] == [
        Estado.CONTINUAR,
        Estado.MUESTRAS_INSUFICIENTES,
        Estado.CONTINUAR,
    ]


def test_si_ninguna_ventana_junto_evidencia_no_se_puede_dar_por_superado():
    resultado, _, _ = correr([sanas(), [], [], []])

    assert resultado.conclusion is Conclusion.SIN_EVIDENCIA


def test_la_duracion_se_redondea_hacia_arriba_a_ventanas_completas():
    resultado, _, _ = correr([sanas()] * 4, duracion_s=12, ventana_s=5)

    assert len(resultado.ventanas) == 3


def test_espera_la_linea_base_y_luego_cada_ventana():
    esperas = []
    ejecutar_experimento(
        experimento_de_prueba(duracion_s=10, ventana_s=5),
        InyectorFalso(),
        SondaFalsa([sanas()] * 3),
        dormir=esperas.append,
    )

    assert esperas == [10, 5, 5]
