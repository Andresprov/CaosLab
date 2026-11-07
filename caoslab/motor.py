from enum import Enum


class Conclusion(str, Enum):
    SUPERADO = "SUPERADO"
    INTERRUMPIDO = "INTERRUMPIDO"


def ejecutar_experimento(experimento, inyector, sonda, dormir=None):
    raise NotImplementedError
