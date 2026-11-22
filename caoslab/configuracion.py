from dataclasses import dataclass
from pathlib import Path

import yaml

from caoslab.modelos import PresupuestoError

TIPOS_DE_FALLO = ("pausar",)
CAMPOS_POSITIVOS = ("duracion_s", "linea_base_s", "ventana_s", "peticiones_por_segundo", "timeout_s")


class ErrorConfiguracion(ValueError):
    pass


@dataclass(frozen=True)
class Experimento:
    nombre: str
    hipotesis: str
    url: str
    contenedor: str
    tipo_fallo: str
    duracion_s: float
    linea_base_s: float
    ventana_s: float
    peticiones_por_segundo: float
    timeout_s: float
    presupuesto: PresupuestoError


def cargar_experimento(ruta) -> Experimento:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfiguracion(f"el archivo {ruta} no existe")

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}

    tipo_fallo = _obligatorio(datos, "fallo", "tipo")
    if tipo_fallo not in TIPOS_DE_FALLO:
        raise ErrorConfiguracion(
            f"el tipo de fallo '{tipo_fallo}' no existe; disponibles: {', '.join(TIPOS_DE_FALLO)}"
        )

    experimento = Experimento(
        nombre=datos.get("nombre", "experimento"),
        hipotesis=_texto(_obligatorio(datos, "hipotesis"), "hipotesis"),
        url=_texto(_obligatorio(datos, "objetivo", "url"), "objetivo.url"),
        contenedor=_texto(_obligatorio(datos, "objetivo", "contenedor"), "objetivo.contenedor"),
        tipo_fallo=tipo_fallo,
        duracion_s=_numero(_obligatorio(datos, "duracion_s"), "duracion_s"),
        linea_base_s=_numero(datos.get("linea_base_s", 10), "linea_base_s"),
        ventana_s=_numero(datos.get("ventana_s", 5), "ventana_s"),
        peticiones_por_segundo=_numero(datos.get("peticiones_por_segundo", 5), "peticiones_por_segundo"),
        timeout_s=_numero(datos.get("timeout_s", 2), "timeout_s"),
        presupuesto=PresupuestoError(
            max_tasa_error=_numero(
                _obligatorio(datos, "presupuesto", "max_tasa_error"), "presupuesto.max_tasa_error"
            ),
            max_latencia_p95_ms=_numero(
                _obligatorio(datos, "presupuesto", "max_latencia_p95_ms"),
                "presupuesto.max_latencia_p95_ms",
            ),
            minimo_muestras=_numero(
                datos["presupuesto"].get("minimo_muestras", 1), "presupuesto.minimo_muestras"
            ),
        ),
    )

    for campo in CAMPOS_POSITIVOS:
        if getattr(experimento, campo) <= 0:
            raise ErrorConfiguracion(f"{campo} debe ser mayor que 0")

    return experimento


def _texto(valor, campo):
    texto = str(valor).strip()
    if not texto:
        raise ErrorConfiguracion(f"el campo obligatorio {campo} está vacío")
    return texto


def _numero(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorConfiguracion(
            f"{campo} debe ser un número, no {type(valor).__name__}: {valor!r}"
        )
    return valor


def _obligatorio(datos, *claves):
    valor = datos
    for clave in claves:
        if not isinstance(valor, dict) or clave not in valor:
            raise ErrorConfiguracion(f"falta el campo obligatorio {'.'.join(claves)}")
        valor = valor[clave]
    return valor
