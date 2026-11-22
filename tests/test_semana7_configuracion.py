"""Semana 7 — casos diseñados para `cargar_experimento()`.

Oráculo: README, sección «experimento.yaml» (campos obligatorios, campos
opcionales con su valor por omisión y el único tipo de fallo de esta entrega) y
la tabla de códigos de salida, que exige que un archivo mal escrito termine en
`ErrorConfiguracion` y no en un error cualquiera, porque el CLI traduce
`ValueError` a código 2.

Tabla de casos en `registro_pruebas.md`, sección 1.2.
"""

import pytest

from caoslab.configuracion import ErrorConfiguracion, cargar_experimento

CAMPOS_POSITIVOS = ("duracion_s", "linea_base_s", "ventana_s", "peticiones_por_segundo", "timeout_s")


# ---------------------------------------------------------------------------
# Partición válida: el archivo completo y el archivo mínimo
# ---------------------------------------------------------------------------


def test_lee_todos_los_campos_de_un_archivo_completo(escribir_experimento):
    ruta = escribir_experimento(
        duracion_s=30,
        linea_base_s=12,
        ventana_s=6,
        peticiones_por_segundo=4,
        timeout_s=3,
        minimo_muestras=10,
        max_tasa_error=0.05,
        max_latencia_p95_ms=500,
    )

    experimento = cargar_experimento(ruta)

    assert experimento.duracion_s == 30
    assert experimento.linea_base_s == 12
    assert experimento.ventana_s == 6
    assert experimento.peticiones_por_segundo == 4
    assert experimento.timeout_s == 3
    assert experimento.tipo_fallo == "pausar"
    assert experimento.presupuesto.max_tasa_error == pytest.approx(0.05)
    assert experimento.presupuesto.max_latencia_p95_ms == pytest.approx(500.0)
    assert experimento.presupuesto.minimo_muestras == 10


@pytest.mark.parametrize(
    "campo, valor_por_omision",
    [
        ("linea_base_s", 10),  # valores por omisión documentados en el README
        ("ventana_s", 5),
        ("peticiones_por_segundo", 5),
        ("timeout_s", 2),
    ],
)
def test_los_campos_opcionales_usan_su_valor_por_omision(
    escribir_experimento, campo, valor_por_omision
):
    experimento = cargar_experimento(escribir_experimento())

    assert getattr(experimento, campo) == valor_por_omision


def test_el_minimo_de_muestras_por_omision_es_uno(escribir_experimento):
    experimento = cargar_experimento(escribir_experimento())

    assert experimento.presupuesto.minimo_muestras == 1


def test_lee_tildes_ene_y_apostrofo_sin_romper_el_texto(
    escribir_experimento, catalogo_experimentos
):
    """Datos sintéticos del conftest: café, ñapa, menú y Café D'Anita."""
    for entrada in catalogo_experimentos:
        ruta = escribir_experimento(
            nombre=f"{entrada['contenedor'].replace('/', '-')}.yaml",
            hipotesis=entrada["hipotesis"],
            url=entrada["url"],
            contenedor=entrada["contenedor"],
        )

        experimento = cargar_experimento(ruta)

        assert experimento.contenedor == entrada["contenedor"]
        assert experimento.url == entrada["url"]
        assert experimento.hipotesis == entrada["hipotesis"]


# ---------------------------------------------------------------------------
# Valores límite de los campos que deben ser mayores que cero
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("campo", CAMPOS_POSITIVOS)
@pytest.mark.parametrize(
    "valor, es_valido",
    [
        (-1, False),  # partición negativa
        (0, False),  # el borde 0 está fuera: la regla dice «mayor que 0»
        (0.1, True),  # primer valor de la partición válida
    ],
)
def test_limites_de_los_campos_que_deben_ser_positivos(
    escribir_experimento, campo, valor, es_valido
):
    ruta = escribir_experimento(**{campo: valor})

    if es_valido:
        assert getattr(cargar_experimento(ruta), campo) == pytest.approx(0.1)
    else:
        with pytest.raises(ErrorConfiguracion, match=f"{campo} debe ser mayor que 0"):
            cargar_experimento(ruta)


# ---------------------------------------------------------------------------
# Particiones inválidas
# ---------------------------------------------------------------------------


def test_un_archivo_que_no_existe_lanza_error_configuracion(tmp_path):
    with pytest.raises(ErrorConfiguracion, match="no existe"):
        cargar_experimento(tmp_path / "no_esta.yaml")


@pytest.mark.parametrize(
    "texto, mensaje",
    [
        ("", "falta el campo obligatorio"),  # archivo vacío: YAML devuelve None
        ("hipotesis: h\n", "falta el campo obligatorio fallo.tipo"),
        (
            "fallo:\n  tipo: pausar\nduracion_s: 30\n"
            "objetivo:\n  url: u\n  contenedor: c\n"
            "presupuesto:\n  max_tasa_error: 0.05\n  max_latencia_p95_ms: 500\n",
            "falta el campo obligatorio hipotesis",
        ),
        (
            "hipotesis: h\nfallo:\n  tipo: pausar\nduracion_s: 30\n"
            "objetivo:\n  contenedor: c\n"
            "presupuesto:\n  max_tasa_error: 0.05\n  max_latencia_p95_ms: 500\n",
            "falta el campo obligatorio objetivo.url",
        ),
        (
            "hipotesis: h\nfallo:\n  tipo: pausar\nduracion_s: 30\n"
            "objetivo:\n  url: u\n"
            "presupuesto:\n  max_tasa_error: 0.05\n  max_latencia_p95_ms: 500\n",
            "falta el campo obligatorio objetivo.contenedor",
        ),
        (
            "hipotesis: h\nfallo:\n  tipo: pausar\n"
            "objetivo:\n  url: u\n  contenedor: c\n"
            "presupuesto:\n  max_tasa_error: 0.05\n  max_latencia_p95_ms: 500\n",
            "falta el campo obligatorio duracion_s",
        ),
        (
            "hipotesis: h\nfallo:\n  tipo: pausar\nduracion_s: 30\n"
            "objetivo:\n  url: u\n  contenedor: c\n"
            "presupuesto:\n  max_latencia_p95_ms: 500\n",
            "falta el campo obligatorio presupuesto.max_tasa_error",
        ),
        (
            "hipotesis: h\nfallo:\n  tipo: pausar\nduracion_s: 30\n"
            "objetivo:\n  url: u\n  contenedor: c\n"
            "presupuesto:\n  max_tasa_error: 0.05\n",
            "falta el campo obligatorio presupuesto.max_latencia_p95_ms",
        ),
    ],
)
def test_cada_campo_obligatorio_que_falta_se_nombra_en_el_error(tmp_path, texto, mensaje):
    ruta = tmp_path / "experimento.yaml"
    ruta.write_text(texto, encoding="utf-8")

    with pytest.raises(ErrorConfiguracion, match=mensaje):
        cargar_experimento(ruta)


@pytest.mark.parametrize(
    "tipo",
    [
        "latencia",  # anunciado para la entrega 2, todavía no existe
        "cpu",
        "matar",
        "PAUSAR",  # el nombre del tipo distingue mayúsculas
        "pausa",  # nombre parecido pero distinto
    ],
)
def test_un_tipo_de_fallo_que_no_existe_lanza_error_configuracion(escribir_experimento, tipo):
    ruta = escribir_experimento(tipo=tipo)

    with pytest.raises(ErrorConfiguracion, match="no existe"):
        cargar_experimento(ruta)


@pytest.mark.parametrize("campo", ["hipotesis", "url", "contenedor"])
@pytest.mark.parametrize("vacio", ["", "   "])
def test_un_campo_de_texto_obligatorio_vacio_lanza_error_configuracion(
    escribir_experimento, campo, vacio
):
    """Un campo obligatorio en blanco es lo mismo que no tenerlo (defecto D-02)."""
    ruta = escribir_experimento(**{campo: vacio})
    nombrado = {"hipotesis": "hipotesis", "url": "objetivo.url", "contenedor": "objetivo.contenedor"}

    with pytest.raises(ErrorConfiguracion, match=f"el campo obligatorio {nombrado[campo]} está vacío"):
        cargar_experimento(ruta)


@pytest.mark.parametrize(
    "campo",
    list(CAMPOS_POSITIVOS) + ["max_tasa_error", "max_latencia_p95_ms", "minimo_muestras"],
)
@pytest.mark.parametrize("valor", ["treinta", "'30 s'"])
def test_un_campo_numerico_con_texto_lanza_error_configuracion(escribir_experimento, campo, valor):
    """El CLI traduce ValueError a código 2; un TypeError se escaparía (defecto D-01)."""
    ruta = escribir_experimento(**{campo: valor})

    with pytest.raises(ErrorConfiguracion, match="debe ser un número"):
        cargar_experimento(ruta)
