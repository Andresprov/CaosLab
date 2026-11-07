from dataclasses import dataclass
from pathlib import Path

import yaml

from caoslab.modelos import PresupuestoError

TIPOS_DE_FALLO = ("pausar",)


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
        hipotesis=str(_obligatorio(datos, "hipotesis")).strip(),
        url=_obligatorio(datos, "objetivo", "url"),
        contenedor=_obligatorio(datos, "objetivo", "contenedor"),
        tipo_fallo=tipo_fallo,
        duracion_s=_obligatorio(datos, "duracion_s"),
        linea_base_s=datos.get("linea_base_s", 10),
        ventana_s=datos.get("ventana_s", 5),
        peticiones_por_segundo=datos.get("peticiones_por_segundo", 5),
        timeout_s=datos.get("timeout_s", 2),
        presupuesto=PresupuestoError(
            max_tasa_error=_obligatorio(datos, "presupuesto", "max_tasa_error"),
            max_latencia_p95_ms=_obligatorio(datos, "presupuesto", "max_latencia_p95_ms"),
            minimo_muestras=datos["presupuesto"].get("minimo_muestras", 1),
        ),
    )

    for campo in ("duracion_s", "linea_base_s", "ventana_s", "peticiones_por_segundo", "timeout_s"):
        if getattr(experimento, campo) <= 0:
            raise ErrorConfiguracion(f"{campo} debe ser mayor que 0")

    return experimento


def _obligatorio(datos, *claves):
    valor = datos
    for clave in claves:
        if not isinstance(valor, dict) or clave not in valor:
            raise ErrorConfiguracion(f"falta el campo obligatorio {'.'.join(claves)}")
        valor = valor[clave]
    return valor
