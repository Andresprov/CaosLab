from typing import Protocol, runtime_checkable

import docker

PREFIJO_CONTENEDOR_PERMITIDO = "caoslab-"


class ErrorInyeccion(RuntimeError):
    """No se pudo inyectar o revertir el fallo: el contenedor no existe, no está permitido o no está corriendo."""


@runtime_checkable
class Inyector(Protocol):
    """Interfaz que espera el motor: inyectar() aplica el fallo y revertir() lo deshace."""
    descripcion: str

    def inyectar(self) -> None: ...

    def revertir(self) -> None: ...


class InyectorPausa:
    """Inyecta el fallo pausando un contenedor de Docker (docker pause).

    Solo actúa sobre contenedores cuyo nombre empieza por PREFIJO_CONTENEDOR_PERMITIDO.

    Recibe:
        contenedor: nombre del contenedor objetivo.
        cliente: cliente de Docker; por defecto docker.from_env(), que lanza
            docker.errors.DockerException si Docker no está encendido.
    """

    def __init__(self, contenedor, cliente=None):
        self.contenedor = contenedor
        self.cliente = cliente or docker.from_env()
        self.descripcion = f"pausar el contenedor {contenedor}"
        self._lo_pause = False

    def inyectar(self):
        """Pausa el contenedor y recuerda que esta instancia lo pausó.

        Lanza:
            ErrorInyeccion: si el contenedor no existe, no está permitido o no está corriendo.
        """
        contenedor = self._buscar()
        if contenedor.status != "running":
            raise ErrorInyeccion(
                f"el contenedor {self.contenedor} no está corriendo (estado: {contenedor.status})"
            )
        contenedor.pause()
        self._lo_pause = True

    def revertir(self):
        """Despausa el contenedor solo si esta instancia lo pausó y sigue pausado.

        Se puede llamar varias veces; sin una inyección previa no toca nada.

        Lanza:
            ErrorInyeccion: si el contenedor desapareció después de pausarlo.
        """
        if not self._lo_pause:
            return
        contenedor = self._buscar()
        if contenedor.status == "paused":
            contenedor.unpause()
        self._lo_pause = False

    def despausar_si_quedo_pausado(self):
        """Despausa el contenedor si quedó pausado de una corrida anterior.

        Devuelve:
            True si estaba pausado y lo despausó; False si no estaba pausado.

        Lanza:
            ErrorInyeccion: si el contenedor no existe o no está permitido.
        """
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
        if not self.contenedor.startswith(PREFIJO_CONTENEDOR_PERMITIDO):
            raise ErrorInyeccion(
                f"el contenedor {self.contenedor} no está permitido: "
                f"su nombre debe empezar por {PREFIJO_CONTENEDOR_PERMITIDO}"
            )
        contenedor.reload()
        return contenedor
