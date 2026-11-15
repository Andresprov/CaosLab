import argparse
import sys

import docker

from caoslab.configuracion import cargar_experimento
from caoslab.informe import escribir_informe, generar_informe
from caoslab.inyectores import ErrorInyeccion, InyectorPausa
from caoslab.motor import Conclusion, ejecutar_experimento
from caoslab.sonda import SondaHTTP

INFORME_POR_DEFECTO = "informe.md"
CODIGO_SUPERADO = 0
CODIGO_NO_SUPERADO = 1
CODIGO_ERROR_DE_USO = 2


def main(argv=None, crear_inyector=InyectorPausa, crear_sonda=SondaHTTP):
    """Punto de entrada del comando caoslab run ARCHIVO [--informe RUTA].

    Carga el experimento, despausa el contenedor si quedó pausado de una corrida
    anterior, corre el experimento, imprime el informe y lo guarda en RUTA.

    Recibe:
        argv: argumentos de la línea de comandos; None usa sys.argv.
        crear_inyector: fábrica del inyector a partir del nombre del contenedor.
        crear_sonda: fábrica de la sonda a partir de url, peticiones por segundo y timeout.

    Devuelve:
        0 si el experimento se superó, 1 si abortó, la línea base fue inestable, no hubo
        evidencia o se interrumpió, y 2 si la configuración es inválida, el contenedor no
        existe o no está permitido, o Docker está apagado.

    Lanza:
        SystemExit: si los argumentos no son válidos (lo hace argparse).
    """
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    argumentos = _leer_argumentos(argv)

    try:
        experimento = cargar_experimento(argumentos.archivo)
        inyector = crear_inyector(experimento.contenedor)
        if inyector.despausar_si_quedo_pausado():
            _avisar(
                f"Aviso: el contenedor {experimento.contenedor} quedó pausado de una corrida "
                "anterior que no terminó bien. Lo despausé antes de empezar."
            )
        sonda = crear_sonda(experimento.url, experimento.peticiones_por_segundo, experimento.timeout_s)
        _avisar(f"Experimento: {experimento.nombre}")
        resultado = ejecutar_experimento(experimento, inyector, sonda, avisar=_avisar)
    except (ValueError, ErrorInyeccion) as error:
        print(f"Error: {error}", file=sys.stderr)
        return CODIGO_ERROR_DE_USO
    except docker.errors.DockerException as error:
        print(f"Error: no pude conectarme a Docker, revisa que esté encendido.\n{error}", file=sys.stderr)
        return CODIGO_ERROR_DE_USO

    print()
    print(generar_informe(resultado))
    escribir_informe(resultado, argumentos.informe)
    print(f"Informe guardado en {argumentos.informe}")

    return CODIGO_SUPERADO if resultado.conclusion is Conclusion.SUPERADO else CODIGO_NO_SUPERADO


def _leer_argumentos(argv):
    lector = argparse.ArgumentParser(prog="caoslab", description="Experimentos de caos controlado sobre Docker.")
    comandos = lector.add_subparsers(dest="comando", required=True)
    correr = comandos.add_parser("run", help="corre un experimento descrito en un archivo YAML")
    correr.add_argument("archivo", help="ruta del experimento, por ejemplo experimento.yaml")
    correr.add_argument(
        "--informe", default=INFORME_POR_DEFECTO, help=f"dónde guardar el informe (por defecto {INFORME_POR_DEFECTO})"
    )
    return lector.parse_args(argv)


def _avisar(texto):
    print(texto, flush=True)
