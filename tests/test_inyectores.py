import docker
import pytest

from caoslab.inyectores import ErrorInyeccion, Inyector, InyectorPausa


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


def test_inyector_pausa_cumple_la_interfaz():
    assert isinstance(InyectorPausa("caoslab-db", ClienteFalso(ContenedorFalso())), Inyector)


def test_inyectar_pausa_el_contenedor():
    contenedor = ContenedorFalso()
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    inyector.inyectar()

    assert contenedor.status == "paused"


def test_revertir_deja_el_contenedor_corriendo_otra_vez():
    contenedor = ContenedorFalso()
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    inyector.inyectar()
    inyector.revertir()

    assert contenedor.status == "running"


def test_revertir_dos_veces_solo_despausa_una():
    contenedor = ContenedorFalso()
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    inyector.inyectar()
    inyector.revertir()
    inyector.revertir()

    assert contenedor.despausas == 1


def test_revertir_sin_haber_inyectado_no_toca_el_contenedor():
    contenedor = ContenedorFalso(status="paused")
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    inyector.revertir()

    assert contenedor.status == "paused"
    assert contenedor.despausas == 0


def test_no_inyecta_si_el_contenedor_no_esta_corriendo():
    contenedor = ContenedorFalso(status="exited")
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    with pytest.raises(ErrorInyeccion, match="exited"):
        inyector.inyectar()
    assert contenedor.pausas == 0


def test_avisa_con_claridad_si_el_contenedor_no_existe():
    inyector = InyectorPausa("no-existe", ClienteFalso(None))

    with pytest.raises(ErrorInyeccion, match="no-existe"):
        inyector.inyectar()


def test_despausa_un_contenedor_que_quedo_pausado_de_una_corrida_anterior():
    contenedor = ContenedorFalso(status="paused")
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    recuperado = inyector.despausar_si_quedo_pausado()

    assert recuperado is True
    assert contenedor.status == "running"


def test_no_hace_nada_si_el_contenedor_ya_estaba_corriendo():
    contenedor = ContenedorFalso()
    inyector = InyectorPausa("caoslab-db", ClienteFalso(contenedor))

    assert inyector.despausar_si_quedo_pausado() is False
    assert contenedor.despausas == 0


@pytest.mark.integracion
def test_pausa_y_despausa_el_contenedor_real_de_la_base_de_datos():
    cliente = docker.from_env()
    inyector = InyectorPausa("caoslab-db", cliente)

    try:
        inyector.inyectar()
        assert cliente.containers.get("caoslab-db").status == "paused"
    finally:
        inyector.revertir()

    assert cliente.containers.get("caoslab-db").status == "running"
