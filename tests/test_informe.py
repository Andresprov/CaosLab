from caoslab.informe import escribir_informe, generar_informe
from caoslab.modelos import Estado, Veredicto
from caoslab.motor import Conclusion, Resultado, Ventana, ejecutar_experimento
from tests.falsos import InyectorFalso, SondaFalsa, experimento_de_prueba, sanas, sin_esperar

SANO = Veredicto(Estado.CONTINUAR, 0.0, 48.2)
ROTO = Veredicto(Estado.ABORTAR, 0.6, 2010.0, ("tasa de error 60.00% supera el máximo de 10.00%",))


def resultado(conclusion, ventanas=(), linea_base=SANO, fallo_inyectado=True):
    return Resultado(
        experimento=experimento_de_prueba(),
        conclusion=conclusion,
        linea_base=linea_base,
        muestras_linea_base=50,
        ventanas=list(ventanas),
        fallo_inyectado=fallo_inyectado,
    )


def test_el_motor_registra_cuantas_muestras_tuvo_la_linea_base():
    hecho = ejecutar_experimento(experimento_de_prueba(), InyectorFalso(), SondaFalsa([sanas(7)] * 4), dormir=sin_esperar)

    assert hecho.muestras_linea_base == 7


def test_incluye_la_hipotesis_el_fallo_y_el_presupuesto():
    texto = generar_informe(resultado(Conclusion.SUPERADO, [Ventana(1, 25, SANO)]))

    assert "El sistema aguanta la pausa." in texto
    assert "fallo falso" not in texto
    assert "pausar" in texto
    assert "caoslab-db" in texto
    assert "10.00 %" in texto
    assert "300 ms" in texto


def test_muestra_la_linea_base_y_cada_ventana_con_sus_metricas():
    texto = generar_informe(resultado(Conclusion.ABORTADO, [Ventana(1, 25, SANO), Ventana(2, 24, ROTO)]))

    assert "50 muestras" in texto
    assert "48.2 ms" in texto
    assert "| 1 | 25 | 0.00 % | 48.2 ms | CONTINUAR |" in texto
    assert "| 2 | 24 | 60.00 % | 2010.0 ms | ABORTAR |" in texto


def test_un_experimento_abortado_dice_en_que_ventana_y_por_que():
    texto = generar_informe(resultado(Conclusion.ABORTADO, [Ventana(1, 25, SANO), Ventana(2, 24, ROTO)]))

    assert "ABORTADO" in texto
    assert "ventana 2" in texto
    assert "tasa de error 60.00% supera el máximo de 10.00%" in texto
    assert "revertido" in texto


def test_un_experimento_superado_confirma_la_hipotesis():
    texto = generar_informe(resultado(Conclusion.SUPERADO, [Ventana(1, 25, SANO)]))

    assert "SUPERADO" in texto
    assert "se sostiene" in texto


def test_si_la_linea_base_falla_explica_que_no_se_inyecto_nada():
    texto = generar_informe(resultado(Conclusion.LINEA_BASE_INESTABLE, linea_base=ROTO, fallo_inyectado=False))

    assert "LINEA_BASE_INESTABLE" in texto
    assert "no se inyectó" in texto.lower()
    assert "tasa de error 60.00%" in texto


def test_un_experimento_interrumpido_lo_dice():
    texto = generar_informe(resultado(Conclusion.INTERRUMPIDO, [Ventana(1, 25, SANO)]))

    assert "INTERRUMPIDO" in texto


def test_escribe_el_mismo_texto_en_un_archivo(tmp_path):
    ruta = tmp_path / "informe.md"
    hecho = resultado(Conclusion.SUPERADO, [Ventana(1, 25, SANO)])

    escribir_informe(hecho, ruta)

    assert ruta.read_text(encoding="utf-8") == generar_informe(hecho)
