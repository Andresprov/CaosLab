"""Datos de prueba sintéticos de la semana 7.

Todo lo que hay aquí es inventado. CaosLab no guarda datos de personas: lo que
consume son nombres de contenedores, URLs, hipótesis y números, así que los
casos difíciles están en el texto (tildes, ñ, apóstrofo, cadenas vacías) y en
los números (ceros y volumen). Los nombres de servicio imitan negocios del
Huila para tener contexto local, pero ninguno corresponde a un negocio real.
"""

import pytest

from caoslab.modelos import Muestra

CATALOGO_SINTETICO = [
    {
        "nombre": "pausa de la base de pedidos",
        "contenedor": "caoslab-pedidos-db",
        "url": "http://localhost:8000/pedidos",
        "hipotesis": "Si la base se congela 30 s, la API responde con menos del 5 % de errores.",
    },
    {
        "nombre": "caída de la réplica de la señal de inventario",
        "contenedor": "caoslab-inventario-ñapa-db",
        "url": "http://localhost:8010/inventario?categoría=café",
        "hipotesis": "La degradación de la réplica no afecta la consulta de artículos.",
    },
    {
        "nombre": "pausa del micrositio Café D'Anita",
        "contenedor": "caoslab-cafe-d'anita-web",
        "url": "http://localhost:8020/menú",
        "hipotesis": "El micrositio sigue mostrando el menú desde la caché.",
    },
    {
        "nombre": "pausa de la pasarela de pagos PSE",
        "contenedor": "caoslab-pagos-pse-api",
        "url": "http://localhost:8030/salud",
        "hipotesis": "Los pagos en curso no se duplican cuando la pasarela se congela.",
    },
]

TEXTOS_VACIOS = ["", "   ", "\t\n"]


@pytest.fixture
def catalogo_experimentos():
    """Cuatro experimentos sintéticos: con tildes, con ñ y con apóstrofo."""
    return [dict(entrada) for entrada in CATALOGO_SINTETICO]


@pytest.fixture
def fabricar_muestras():
    """Fábrica de tandas de muestras sintéticas con latencias controladas."""

    def fabricar(exitosas=0, fallidas=0, latencia_ms=100.0, latencia_de_las_fallidas=None):
        latencia_fallida = (
            latencia_ms if latencia_de_las_fallidas is None else latencia_de_las_fallidas
        )
        return [Muestra(True, latencia_ms) for _ in range(exitosas)] + [
            Muestra(False, latencia_fallida) for _ in range(fallidas)
        ]

    return fabricar


@pytest.fixture
def tanda_de_volumen(fabricar_muestras):
    """300 muestras: 15 fallidas y un pico aislado, para probar el volumen.

    285 exitosas de 80 ms, 15 fallidas de 80 ms y un pico de 9000 ms que queda
    por encima del percentil 95 (índice ceil(0.95 * 301) - 1 = 286).
    """
    return fabricar_muestras(exitosas=285, fallidas=15, latencia_ms=80.0) + [
        Muestra(True, 9000.0)
    ]


@pytest.fixture
def escribir_experimento(tmp_path):
    """Escribe un experimento.yaml sintético y devuelve su ruta."""

    def escribir(nombre="experimento.yaml", **cambios):
        campos = {
            "hipotesis": "La API aguanta la pausa de la base.",
            "url": "http://localhost:8000/pedidos",
            "contenedor": "caoslab-pedidos-db",
            "tipo": "pausar",
            "duracion_s": 30,
            "max_tasa_error": 0.05,
            "max_latencia_p95_ms": 500,
        }
        campos.update(cambios)
        opcionales = "".join(
            f"{clave}: {campos[clave]}\n"
            for clave in ("linea_base_s", "ventana_s", "peticiones_por_segundo", "timeout_s")
            if clave in campos
        )
        minimo = (
            f"  minimo_muestras: {campos['minimo_muestras']}\n"
            if "minimo_muestras" in campos
            else ""
        )
        ruta = tmp_path / nombre
        ruta.write_text(
            f"nombre: {campos.get('nombre_experimento', 'experimento sintético')}\n"
            f"hipotesis: {campos['hipotesis']!r}\n"
            "objetivo:\n"
            f"  url: {campos['url']!r}\n"
            f"  contenedor: {campos['contenedor']!r}\n"
            "fallo:\n"
            f"  tipo: {campos['tipo']}\n"
            f"duracion_s: {campos['duracion_s']}\n"
            f"{opcionales}"
            "presupuesto:\n"
            f"  max_tasa_error: {campos['max_tasa_error']}\n"
            f"  max_latencia_p95_ms: {campos['max_latencia_p95_ms']}\n"
            f"{minimo}",
            encoding="utf-8",
        )
        return ruta

    return escribir
