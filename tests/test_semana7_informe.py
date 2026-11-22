"""Semana 7 — casos diseñados para `generar_informe()` y `escribir_informe()`.

Oráculo: DOCUMENTACION.txt, sección 9: el informe lleva la hipótesis, la
configuración, la línea base, una tabla con cada ventana, el veredicto con una
frase que lo explica, los motivos si hubo y si el fallo se revirtió; los motivos
salen de la ventana que abortó o, si falló la línea base, de la línea base, y
cuando la línea base falló por falta de muestras el motivo dice cuántas juntó y
cuántas hacían falta.

Usa los datos sintéticos del conftest. Tabla de casos en
`registro_pruebas.md`, sección 1.5.
"""

import pytest

from caoslab.informe import escribir_informe, generar_informe
from caoslab.modelos import PresupuestoError
from caoslab.motor import Conclusion, ejecutar_experimento
from tests.falsos import InyectorFalso, SondaFalsa, experimento_de_prueba, fallidas, sanas, sin_esperar


def resultado_de(tandas, **cambios):
    return ejecutar_experimento(
        experimento_de_prueba(**cambios), InyectorFalso(), SondaFalsa(tandas), dormir=sin_esperar
    )


TANDAS = {
    Conclusion.SUPERADO: [sanas()] * 4,
    Conclusion.ABORTADO: [sanas(), sanas(), fallidas(), sanas()],
    Conclusion.LINEA_BASE_INESTABLE: [fallidas(10)] + [sanas()] * 3,
    Conclusion.SIN_EVIDENCIA: [sanas(), [], [], []],
}


# ---------------------------------------------------------------------------
# Particiones por conclusión: cada una tiene su propia frase y sus motivos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "conclusion, hay_motivos, texto_de_reversion",
    [
        (Conclusion.SUPERADO, False, "Fallo revertido"),
        (Conclusion.ABORTADO, True, "Fallo revertido"),
        (Conclusion.LINEA_BASE_INESTABLE, True, "No se inyectó ningún fallo"),
        (Conclusion.SIN_EVIDENCIA, False, "Fallo revertido"),
    ],
)
def test_el_informe_nombra_el_veredicto_y_si_se_revirtio(
    conclusion, hay_motivos, texto_de_reversion
):
    resultado = resultado_de(TANDAS[conclusion])
    assert resultado.conclusion is conclusion  # el caso quedó bien armado

    informe = generar_informe(resultado)

    assert f"**{conclusion.value}**" in informe
    assert ("Motivos:" in informe) is hay_motivos
    assert texto_de_reversion in informe


def test_los_motivos_de_un_aborto_salen_de_la_ventana_que_aborto():
    resultado = resultado_de(TANDAS[Conclusion.ABORTADO])

    informe = generar_informe(resultado)

    for motivo in resultado.ventanas[-1].veredicto.motivos:
        assert f"- {motivo}" in informe


def test_los_motivos_de_una_linea_base_inestable_salen_de_la_linea_base():
    resultado = resultado_de(TANDAS[Conclusion.LINEA_BASE_INESTABLE])

    informe = generar_informe(resultado)

    for motivo in resultado.linea_base.motivos:
        assert f"- {motivo}" in informe
    assert "El fallo no se llegó a inyectar." in informe


def test_si_la_linea_base_no_junto_muestras_el_motivo_dice_cuantas_faltaron():
    """La regla pide los dos números: las que juntó y el mínimo exigido."""
    resultado = resultado_de([sanas(3)] + [sanas()] * 3)

    informe = generar_informe(resultado)

    assert "solo juntó 3 muestras" in informe
    assert "el mínimo es 5" in informe


@pytest.mark.parametrize(
    "duracion_s, ventana_s, filas_esperadas",
    [
        (15, 5, 3),  # una fila por ventana medida
        (10, 5, 2),
        (5, 5, 1),
    ],
)
def test_la_tabla_lleva_una_fila_por_ventana_medida(duracion_s, ventana_s, filas_esperadas):
    resultado = resultado_de([sanas()] * 5, duracion_s=duracion_s, ventana_s=ventana_s)

    informe = generar_informe(resultado)
    filas = [
        linea
        for linea in informe.splitlines()
        if linea.startswith("| ") and not linea.startswith("| Ventana") and "---" not in linea
    ]

    assert len(filas) == filas_esperadas


# ---------------------------------------------------------------------------
# Datos sintéticos: tildes, ñ y apóstrofo tienen que salir tal cual
# ---------------------------------------------------------------------------


def test_el_informe_conserva_tildes_ene_y_apostrofo(catalogo_experimentos):
    for entrada in catalogo_experimentos:
        resultado = resultado_de(
            [sanas()] * 4,
            nombre=entrada["nombre"],
            hipotesis=entrada["hipotesis"],
            contenedor=entrada["contenedor"],
            url=entrada["url"],
        )

        informe = generar_informe(resultado)

        assert f"# Informe del experimento: {entrada['nombre']}" in informe
        assert entrada["hipotesis"] in informe
        assert entrada["contenedor"] in informe
        assert entrada["url"] in informe


def test_el_archivo_del_informe_se_guarda_en_utf8(tmp_path, catalogo_experimentos):
    entrada = catalogo_experimentos[2]  # Café D'Anita: tilde y apóstrofo
    resultado = resultado_de([sanas()] * 4, nombre=entrada["nombre"], contenedor=entrada["contenedor"])
    ruta = tmp_path / "informe.md"

    escribir_informe(resultado, ruta)

    assert ruta.read_text(encoding="utf-8") == generar_informe(resultado)
    assert entrada["contenedor"] in ruta.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Límites del formato de números
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "max_tasa_error, porcentaje_esperado",
    [
        (0.0, "0.00 %"),  # borde inferior: cualquier fallo agota el presupuesto
        (0.05, "5.00 %"),
        (0.125, "12.50 %"),  # dos decimales, sin redondear a 13 %
        (1.0, "100.00 %"),  # borde superior
    ],
)
def test_el_presupuesto_se_imprime_con_dos_decimales(max_tasa_error, porcentaje_esperado):
    presupuesto = PresupuestoError(max_tasa_error, 500.0, minimo_muestras=5)
    resultado = resultado_de([sanas()] * 4, presupuesto=presupuesto)

    informe = generar_informe(resultado)

    assert f"tasa de error máxima {porcentaje_esperado}" in informe
