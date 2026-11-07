import docker
import pytest

from caoslab.cli import main

pytestmark = pytest.mark.integracion

PLANTILLA = """
hipotesis: prueba de extremo a extremo
objetivo:
  url: http://localhost:8000{ruta}
  contenedor: caoslab-db
fallo:
  tipo: pausar
duracion_s: 4
linea_base_s: 2
ventana_s: 2
peticiones_por_segundo: 10
timeout_s: 1
presupuesto:
  max_tasa_error: 0.05
  max_latencia_p95_ms: 500
  minimo_muestras: 5
"""


def correr(tmp_path, ruta):
    archivo = tmp_path / "experimento.yaml"
    archivo.write_text(PLANTILLA.format(ruta=ruta), encoding="utf-8")
    informe = tmp_path / "informe.md"
    codigo = main(["run", str(archivo), "--informe", str(informe)])
    return codigo, informe.read_text(encoding="utf-8")


def estado_de_la_base():
    return docker.from_env().containers.get("caoslab-db").status


def test_pausar_la_base_agota_el_presupuesto_de_pedidos_y_la_deja_corriendo(tmp_path):
    codigo, informe = correr(tmp_path, "/pedidos")

    assert codigo == 1
    assert "**ABORTADO**" in informe
    assert "tasa de error" in informe
    assert estado_de_la_base() == "running"


def test_health_no_depende_de_la_base_y_el_experimento_se_supera(tmp_path):
    codigo, informe = correr(tmp_path, "/health")

    assert codigo == 0
    assert "**SUPERADO**" in informe
    assert estado_de_la_base() == "running"
