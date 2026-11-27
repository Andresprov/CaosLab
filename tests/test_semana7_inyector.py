"""Semana 7 — casos diseñados para `InyectorPausa`.

Oráculo: README, secciones «Cómo decide el motor» y «Reversión garantizada»,
y la tabla de códigos de salida: un contenedor inexistente o en un estado que
no se puede pausar termina en código 2, es decir en `ErrorInyeccion`.
Tabla de casos en `registro_pruebas.md`, sección 1.4.
"""

import docker
import pytest

from caoslab.inyectores import ErrorInyeccion, InyectorPausa

ESTADOS_QUE_NO_SE_PUEDEN_PAUSAR = ["paused", "exited", "created", "restarting", "dead"]


class ContenedorFalso:
    def __init__(self, status="running"):
        self.status = status
        self.pausas = 0
        self.despausas = 0

    def reload(self):
        pass

    def pause(self):
        self.pausas += 1
        self.status = "paused"

    def unpause(self):
        self.despausas += 1
        self.status = "running"


class ClienteFalso:
    def __init__(self, contenedor=None):
        self.contenedor = contenedor
        self.containers = self

    def get(self, nombre):
        if self.contenedor is None:
            raise docker.errors.NotFound(f"No such container: {nombre}")
        return self.contenedor


def inyector_con(contenedor):
    return InyectorPausa("pedidos-db", ClienteFalso(contenedor))


# ---------------------------------------------------------------------------
# Particiones del estado del contenedor al inyectar
# ---------------------------------------------------------------------------


def test_pausa_el_contenedor_cuando_esta_corriendo():
    contenedor = ContenedorFalso("running")

    inyector_con(contenedor).inyectar()

    assert contenedor.pausas == 1
    assert contenedor.status == "paused"


@pytest.mark.parametrize("status", ESTADOS_QUE_NO_SE_PUEDEN_PAUSAR)
def test_un_contenedor_que_no_esta_corriendo_lanza_error_inyeccion(status):
    contenedor = ContenedorFalso(status)

    with pytest.raises(ErrorInyeccion, match=f"no está corriendo \\(estado: {status}\\)"):
        inyector_con(contenedor).inyectar()

    assert contenedor.pausas == 0


def test_un_contenedor_que_no_existe_lanza_error_inyeccion():
    with pytest.raises(ErrorInyeccion, match="no existe el contenedor pedidos-db"):
        inyector_con(None).inyectar()


# ---------------------------------------------------------------------------
# Tabla de decisión de revertir()
#   C1: este inyector fue el que pausó el contenedor
#   C2: el contenedor sigue pausado ahora
# Solo se despausa cuando las dos son «sí»: revertir nunca toca un contenedor
# que no pausó este experimento.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lo_pauso, status_al_revertir, despausas_esperadas",
    [
        (False, "paused", 0),  # R1: C1 no, C2 sí -> no es nuestro, no se toca
        (False, "running", 0),  # R2: C1 no, C2 no -> nada que hacer
        (True, "running", 0),  # R3: C1 sí, C2 no -> alguien ya lo despausó
        (True, "paused", 1),  # R4: C1 sí, C2 sí -> el único caso que despausa
    ],
)
def test_tabla_de_decision_de_revertir(lo_pauso, status_al_revertir, despausas_esperadas):
    contenedor = ContenedorFalso("running")
    inyector = inyector_con(contenedor)
    if lo_pauso:
        inyector.inyectar()
    contenedor.status = status_al_revertir

    inyector.revertir()

    assert contenedor.despausas == despausas_esperadas


def test_revertir_dos_veces_despausa_una_sola_vez():
    """Límite: el motor llama revertir() en un finally, puede llegar repetido."""
    contenedor = ContenedorFalso("running")
    inyector = inyector_con(contenedor)
    inyector.inyectar()

    inyector.revertir()
    inyector.revertir()

    assert contenedor.despausas == 1
    assert contenedor.status == "running"


# ---------------------------------------------------------------------------
# Rescate de una corrida anterior matada a la fuerza
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, rescatado, despausas_esperadas",
    [
        ("paused", True, 1),  # quedó pausado de una corrida que no terminó bien
        ("running", False, 0),  # está sano: no hay nada que rescatar
        ("exited", False, 0),  # está apagado: tampoco se despausa
    ],
)
def test_despausar_si_quedo_pausado(status, rescatado, despausas_esperadas):
    contenedor = ContenedorFalso(status)

    assert inyector_con(contenedor).despausar_si_quedo_pausado() is rescatado
    assert contenedor.despausas == despausas_esperadas


def test_la_descripcion_nombra_el_contenedor_objetivo():
    """El informe y la consola imprimen esta descripción."""
    assert inyector_con(ContenedorFalso()).descripcion == "pausar el contenedor pedidos-db"
