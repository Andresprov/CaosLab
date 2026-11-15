from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from caoslab.inyectores import PREFIJO_CONTENEDOR_PERMITIDO
from caoslab.modelos import PresupuestoError

TIPOS_DE_FALLO = ("pausar",)
ESQUEMAS_PERMITIDOS = ("http", "https")
HOSTS_PERMITIDOS = ("localhost", "127.0.0.1", "::1")
DURACION_MAXIMA_S = 120
MAX_PETICIONES_POR_SEGUNDO = 50
NOMBRE_POR_DEFECTO = "experimento"
VALORES_POR_DEFECTO = {"linea_base_s": 10, "ventana_s": 5, "peticiones_por_segundo": 5, "timeout_s": 2}
MINIMO_MUESTRAS_POR_DEFECTO = 1
CAMPOS_DE_TIEMPO_Y_CARGA = ("duracion_s", "linea_base_s", "ventana_s", "peticiones_por_segundo", "timeout_s")
CAMPOS_DEL_PRESUPUESTO = ("max_tasa_error", "max_latencia_p95_ms", "minimo_muestras")


class ErrorConfiguracion(ValueError):
    """Error en el contenido de experimento.yaml. Hereda de ValueError."""


@dataclass(frozen=True)
class Experimento:
    """Experimento ya validado, tal como lo usa el motor. Es inmutable."""
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
    """Lee y valida un experimento descrito en un archivo YAML.

    Recibe:
        ruta: ruta del archivo, como texto o Path.

    Devuelve:
        Un Experimento con los valores por defecto aplicados a los campos opcionales
        (VALORES_POR_DEFECTO y MINIMO_MUESTRAS_POR_DEFECTO).

    Lanza:
        ErrorConfiguracion: si el archivo no existe, falta un campo obligatorio, el tipo
            de fallo no existe, la url no es http(s) hacia localhost, 127.0.0.1 o ::1, el
            contenedor no empieza por caoslab-, un campo numérico no es un número o no es
            mayor que 0, duracion_s pasa de 120 o peticiones_por_segundo pasa de 50.
        yaml.YAMLError: si el archivo no es YAML válido.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfiguracion(f"el archivo {ruta} no existe")

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}

    experimento = _construir(datos)
    _validar(experimento)
    return experimento


def _construir(datos):
    tipo_fallo = _obligatorio(datos, "fallo", "tipo")
    if tipo_fallo not in TIPOS_DE_FALLO:
        raise ErrorConfiguracion(
            f"el tipo de fallo '{tipo_fallo}' no existe; disponibles: {', '.join(TIPOS_DE_FALLO)}"
        )
    opcionales = {campo: datos.get(campo, valor) for campo, valor in VALORES_POR_DEFECTO.items()}
    return Experimento(
        nombre=datos.get("nombre", NOMBRE_POR_DEFECTO),
        hipotesis=str(_obligatorio(datos, "hipotesis")).strip(),
        url=_obligatorio(datos, "objetivo", "url"),
        contenedor=_obligatorio(datos, "objetivo", "contenedor"),
        tipo_fallo=tipo_fallo,
        duracion_s=_obligatorio(datos, "duracion_s"),
        **opcionales,
        presupuesto=PresupuestoError(
            max_tasa_error=_obligatorio(datos, "presupuesto", "max_tasa_error"),
            max_latencia_p95_ms=_obligatorio(datos, "presupuesto", "max_latencia_p95_ms"),
            minimo_muestras=datos["presupuesto"].get("minimo_muestras", MINIMO_MUESTRAS_POR_DEFECTO),
        ),
    )


def _validar(experimento):
    _validar_url(experimento.url)
    _validar_contenedor(experimento.contenedor)
    for campo in CAMPOS_DE_TIEMPO_Y_CARGA:
        _validar_numero(campo, getattr(experimento, campo))
    for campo in CAMPOS_DEL_PRESUPUESTO:
        _validar_numero(f"presupuesto.{campo}", getattr(experimento.presupuesto, campo))
    for campo in CAMPOS_DE_TIEMPO_Y_CARGA:
        if getattr(experimento, campo) <= 0:
            raise ErrorConfiguracion(f"{campo} debe ser mayor que 0")
    if experimento.duracion_s > DURACION_MAXIMA_S:
        raise ErrorConfiguracion(f"duracion_s no puede pasar de {DURACION_MAXIMA_S} s")
    if experimento.peticiones_por_segundo > MAX_PETICIONES_POR_SEGUNDO:
        raise ErrorConfiguracion(f"peticiones_por_segundo no puede pasar de {MAX_PETICIONES_POR_SEGUNDO}")


def _obligatorio(datos, *claves):
    valor = datos
    for clave in claves:
        if not isinstance(valor, dict) or clave not in valor:
            raise ErrorConfiguracion(f"falta el campo obligatorio {'.'.join(claves)}")
        valor = valor[clave]
    return valor


def _validar_numero(campo, valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorConfiguracion(f"{campo} debe ser un número, no {valor!r}")


def _validar_url(url):
    partes = urlsplit(str(url))
    if partes.scheme not in ESQUEMAS_PERMITIDOS:
        raise ErrorConfiguracion(
            f"la url {url} debe usar {' o '.join(ESQUEMAS_PERMITIDOS)}; otros esquemas como file:// no se permiten"
        )
    if partes.hostname not in HOSTS_PERMITIDOS:
        raise ErrorConfiguracion(
            f"la url {url} apunta a {partes.hostname}; CaosLab solo mide la copia local "
            f"({', '.join(HOSTS_PERMITIDOS)})"
        )


def _validar_contenedor(contenedor):
    if not str(contenedor).startswith(PREFIJO_CONTENEDOR_PERMITIDO):
        raise ErrorConfiguracion(
            f"el contenedor {contenedor} no está permitido; CaosLab solo inyecta fallos en contenedores "
            f"cuyo nombre empieza por {PREFIJO_CONTENEDOR_PERMITIDO}"
        )
