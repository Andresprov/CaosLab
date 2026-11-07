import pytest

from caoslab.configuracion import ErrorConfiguracion, cargar_experimento
from caoslab.modelos import PresupuestoError

YAML_COMPLETO = """
nombre: pausa de la base de datos
hipotesis: Si la base de datos se pausa, /pedidos sigue dentro del presupuesto.
objetivo:
  url: http://localhost:8000/pedidos
  contenedor: caoslab-db
fallo:
  tipo: pausar
duracion_s: 30
linea_base_s: 8
ventana_s: 4
peticiones_por_segundo: 10
timeout_s: 1.5
presupuesto:
  max_tasa_error: 0.05
  max_latencia_p95_ms: 500
  minimo_muestras: 10
"""

YAML_MINIMO = """
hipotesis: La API aguanta.
objetivo:
  url: http://localhost:8000/pedidos
  contenedor: caoslab-db
fallo:
  tipo: pausar
duracion_s: 20
presupuesto:
  max_tasa_error: 0.1
  max_latencia_p95_ms: 300
"""


def escribir(tmp_path, texto):
    ruta = tmp_path / "experimento.yaml"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def test_lee_todos_los_campos_del_archivo(tmp_path):
    experimento = cargar_experimento(escribir(tmp_path, YAML_COMPLETO))

    assert experimento.nombre == "pausa de la base de datos"
    assert experimento.hipotesis.startswith("Si la base de datos se pausa")
    assert experimento.url == "http://localhost:8000/pedidos"
    assert experimento.contenedor == "caoslab-db"
    assert experimento.tipo_fallo == "pausar"
    assert experimento.duracion_s == 30
    assert experimento.linea_base_s == 8
    assert experimento.ventana_s == 4
    assert experimento.peticiones_por_segundo == 10
    assert experimento.timeout_s == 1.5
    assert experimento.presupuesto == PresupuestoError(0.05, 500, 10)


def test_usa_valores_por_defecto_para_los_campos_opcionales(tmp_path):
    experimento = cargar_experimento(escribir(tmp_path, YAML_MINIMO))

    assert experimento.nombre == "experimento"
    assert experimento.linea_base_s == 10
    assert experimento.ventana_s == 5
    assert experimento.peticiones_por_segundo == 5
    assert experimento.timeout_s == 2
    assert experimento.presupuesto.minimo_muestras == 1


def test_falla_nombrando_el_campo_obligatorio_que_falta(tmp_path):
    texto = YAML_MINIMO.replace("  contenedor: caoslab-db\n", "")

    with pytest.raises(ErrorConfiguracion, match="objetivo.contenedor"):
        cargar_experimento(escribir(tmp_path, texto))


def test_rechaza_un_tipo_de_fallo_que_todavia_no_existe(tmp_path):
    texto = YAML_MINIMO.replace("tipo: pausar", "tipo: latencia")

    with pytest.raises(ErrorConfiguracion, match="latencia"):
        cargar_experimento(escribir(tmp_path, texto))


def test_rechaza_una_duracion_que_no_es_positiva(tmp_path):
    texto = YAML_MINIMO.replace("duracion_s: 20", "duracion_s: 0")

    with pytest.raises(ErrorConfiguracion, match="duracion_s"):
        cargar_experimento(escribir(tmp_path, texto))


def test_falla_con_un_mensaje_claro_si_el_archivo_no_existe(tmp_path):
    with pytest.raises(ErrorConfiguracion, match="no existe"):
        cargar_experimento(tmp_path / "no_esta.yaml")
