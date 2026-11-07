import docker
import pytest

from caoslab.cli import main
from tests.falsos import InyectorFalso, SondaFalsa, fallidas, sanas

YAML_RAPIDO = """
nombre: prueba del cli
hipotesis: La API aguanta la pausa.
objetivo:
  url: http://localhost:8000/pedidos
  contenedor: caoslab-db
fallo:
  tipo: pausar
duracion_s: 0.2
linea_base_s: 0.05
ventana_s: 0.1
presupuesto:
  max_tasa_error: 0.1
  max_latencia_p95_ms: 300
  minimo_muestras: 5
"""


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "experimento.yaml").write_text(YAML_RAPIDO, encoding="utf-8")
    return tmp_path


def correr(tandas, inyector=None):
    inyector = inyector or InyectorFalso()
    codigo = main(
        ["run", "experimento.yaml"],
        crear_inyector=lambda contenedor: inyector,
        crear_sonda=lambda url, rps, timeout: SondaFalsa(tandas),
    )
    return codigo, inyector


def test_un_experimento_superado_sale_con_codigo_0_y_guarda_el_informe(carpeta, capsys):
    codigo, inyector = correr([sanas()] * 3)

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "SUPERADO" in salida
    assert "Ventana 1" in salida
    assert inyector.eventos == ["inyectar", "revertir"]
    assert "SUPERADO" in (carpeta / "informe.md").read_text(encoding="utf-8")


def test_un_experimento_abortado_sale_con_codigo_1(carpeta, capsys):
    codigo, inyector = correr([sanas(), fallidas(), sanas()])

    assert codigo == 1
    assert "ABORTADO" in capsys.readouterr().out
    assert inyector.eventos == ["inyectar", "revertir"]


def test_una_configuracion_invalida_sale_con_codigo_2_y_explica_el_error(carpeta, capsys):
    (carpeta / "experimento.yaml").write_text("hipotesis: nada mas\n", encoding="utf-8")

    codigo, _ = correr([])

    assert codigo == 2
    assert "falta el campo obligatorio" in capsys.readouterr().err


def test_si_docker_no_esta_encendido_sale_con_codigo_2(carpeta, capsys):
    def sin_docker(contenedor):
        raise docker.errors.DockerException("Error while fetching server API version")

    codigo = main(["run", "experimento.yaml"], crear_inyector=sin_docker, crear_sonda=None)

    assert codigo == 2
    assert "Docker" in capsys.readouterr().err


def test_avisa_si_el_contenedor_quedo_pausado_de_una_corrida_anterior(carpeta, capsys):
    inyector = InyectorFalso(quedo_pausado=True)

    correr([sanas()] * 3, inyector)

    assert "quedó pausado" in capsys.readouterr().out


def test_permite_elegir_donde_guardar_el_informe(carpeta):
    main(
        ["run", "experimento.yaml", "--informe", "salida.md"],
        crear_inyector=lambda contenedor: InyectorFalso(),
        crear_sonda=lambda url, rps, timeout: SondaFalsa([sanas()] * 3),
    )

    assert (carpeta / "salida.md").exists()
