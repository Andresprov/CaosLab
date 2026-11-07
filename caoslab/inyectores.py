from typing import Protocol, runtime_checkable


class ErrorInyeccion(RuntimeError):
    pass


@runtime_checkable
class Inyector(Protocol):
    descripcion: str

    def inyectar(self) -> None: ...

    def revertir(self) -> None: ...


class InyectorPausa:
    def __init__(self, contenedor, cliente=None):
        self.descripcion = f"pausar el contenedor {contenedor}"

    def inyectar(self):
        raise NotImplementedError

    def revertir(self):
        raise NotImplementedError

    def despausar_si_quedo_pausado(self):
        raise NotImplementedError
