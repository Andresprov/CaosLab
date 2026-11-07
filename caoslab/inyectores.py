from typing import Protocol, runtime_checkable

import docker


class ErrorInyeccion(RuntimeError):
    pass


@runtime_checkable
class Inyector(Protocol):
    descripcion: str

    def inyectar(self) -> None: ...

    def revertir(self) -> None: ...


class InyectorPausa:
    def __init__(self, contenedor, cliente=None):
        self.contenedor = contenedor
        self.cliente = cliente or docker.from_env()
        self.descripcion = f"pausar el contenedor {contenedor}"
        self._lo_pause = False

    def inyectar(self):
        contenedor = self._buscar()
        if contenedor.status != "running":
            raise ErrorInyeccion(
                f"el contenedor {self.contenedor} no está corriendo (estado: {contenedor.status})"
            )
        contenedor.pause()
        self._lo_pause = True

    def revertir(self):
        if not self._lo_pause:
            return
        contenedor = self._buscar()
        if contenedor.status == "paused":
            contenedor.unpause()
        self._lo_pause = False

    def despausar_si_quedo_pausado(self):
        contenedor = self._buscar()
        if contenedor.status != "paused":
            return False
        contenedor.unpause()
        return True

    def _buscar(self):
        try:
            contenedor = self.cliente.containers.get(self.contenedor)
        except docker.errors.NotFound:
            raise ErrorInyeccion(f"no existe el contenedor {self.contenedor}") from None
        contenedor.reload()
        return contenedor
