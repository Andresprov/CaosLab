import math
import signal
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from caoslab.configuracion import Experimento
from caoslab.estado_estable import evaluar_estado_estable
from caoslab.modelos import Estado, Veredicto

SENALES_DE_PARADA = [
    getattr(signal, nombre) for nombre in ("SIGINT", "SIGTERM", "SIGBREAK") if hasattr(signal, nombre)
]


class Conclusion(str, Enum):
    SUPERADO = "SUPERADO"
    ABORTADO = "ABORTADO"
    LINEA_BASE_INESTABLE = "LINEA_BASE_INESTABLE"
    SIN_EVIDENCIA = "SIN_EVIDENCIA"
    INTERRUMPIDO = "INTERRUMPIDO"


@dataclass(frozen=True)
class Ventana:
    numero: int
    muestras: int
    veredicto: Veredicto


@dataclass
class Resultado:
    experimento: Experimento
    conclusion: Conclusion
    linea_base: Veredicto | None = None
    ventanas: list[Ventana] = field(default_factory=list)
    fallo_inyectado: bool = False


def ejecutar_experimento(experimento, inyector, sonda, dormir=None):
    parar = threading.Event()
    dormir = dormir or (lambda segundos: _esperar(parar, segundos))
    anteriores = _capturar_senales(parar)
    try:
        sonda.iniciar()
        return _correr(experimento, inyector, sonda, dormir, parar)
    finally:
        sonda.detener()
        _restaurar_senales(anteriores)


def _correr(experimento, inyector, sonda, dormir, parar):
    resultado = Resultado(experimento, Conclusion.INTERRUMPIDO)

    dormir(experimento.linea_base_s)
    muestras = sonda.recoger()
    if parar.is_set():
        return resultado
    resultado.linea_base = evaluar_estado_estable(muestras, experimento.presupuesto)
    if resultado.linea_base.estado is not Estado.CONTINUAR:
        resultado.conclusion = Conclusion.LINEA_BASE_INESTABLE
        return resultado

    try:
        resultado.fallo_inyectado = True
        inyector.inyectar()
        resultado.conclusion = _vigilar(experimento, sonda, dormir, parar, resultado.ventanas)
    finally:
        inyector.revertir()

    return resultado


def _vigilar(experimento, sonda, dormir, parar, ventanas):
    total = math.ceil(experimento.duracion_s / experimento.ventana_s)
    for numero in range(1, total + 1):
        dormir(experimento.ventana_s)
        muestras = sonda.recoger()
        if parar.is_set():
            return Conclusion.INTERRUMPIDO
        veredicto = evaluar_estado_estable(muestras, experimento.presupuesto)
        ventanas.append(Ventana(numero, len(muestras), veredicto))
        if veredicto.estado is Estado.ABORTAR:
            return Conclusion.ABORTADO
    if all(v.veredicto.estado is Estado.MUESTRAS_INSUFICIENTES for v in ventanas):
        return Conclusion.SIN_EVIDENCIA
    return Conclusion.SUPERADO


def _esperar(parar, segundos):
    limite = time.monotonic() + segundos
    while not parar.is_set():
        restante = limite - time.monotonic()
        if restante <= 0:
            return
        parar.wait(min(restante, 0.2))


def _capturar_senales(parar):
    if threading.current_thread() is not threading.main_thread():
        return {}
    return {senal: signal.signal(senal, lambda *_: parar.set()) for senal in SENALES_DE_PARADA}


def _restaurar_senales(anteriores):
    for senal, manejador in anteriores.items():
        signal.signal(senal, manejador)
