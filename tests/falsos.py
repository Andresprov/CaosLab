from caoslab.configuracion import Experimento
from caoslab.modelos import Muestra, PresupuestoError


def experimento_de_prueba(duracion_s=15, ventana_s=5, **cambios):
    datos = dict(
        nombre="prueba",
        hipotesis="El sistema aguanta la pausa.",
        url="http://localhost:8000/pedidos",
        contenedor="caoslab-db",
        tipo_fallo="pausar",
        duracion_s=duracion_s,
        linea_base_s=10,
        ventana_s=ventana_s,
        peticiones_por_segundo=5,
        timeout_s=2,
        presupuesto=PresupuestoError(max_tasa_error=0.1, max_latencia_p95_ms=300, minimo_muestras=5),
    )
    datos.update(cambios)
    return Experimento(**datos)


def sanas(cantidad=10, latencia_ms=50.0):
    return [Muestra(exitosa=True, latencia_ms=latencia_ms) for _ in range(cantidad)]


def fallidas(cantidad=10, latencia_ms=2000.0):
    return [Muestra(exitosa=False, latencia_ms=latencia_ms) for _ in range(cantidad)]


class InyectorFalso:
    def __init__(self, falla_al_inyectar=False):
        self.descripcion = "fallo falso en memoria"
        self.eventos = []
        self.falla_al_inyectar = falla_al_inyectar

    def inyectar(self):
        self.eventos.append("inyectar")
        if self.falla_al_inyectar:
            raise RuntimeError("no se pudo inyectar")

    def revertir(self):
        self.eventos.append("revertir")


class SondaFalsa:
    def __init__(self, tandas, al_recoger=None):
        self.tandas = list(tandas)
        self.al_recoger = al_recoger or {}
        self.recogidas = 0
        self.iniciada = False
        self.detenida = False

    def iniciar(self):
        self.iniciada = True

    def recoger(self):
        self.recogidas += 1
        accion = self.al_recoger.get(self.recogidas)
        if accion:
            accion()
        return self.tandas.pop(0) if self.tandas else []

    def detener(self):
        self.detenida = True


def sin_esperar(segundos):
    pass
