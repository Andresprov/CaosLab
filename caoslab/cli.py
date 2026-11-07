import argparse
import sys

import docker

from caoslab.configuracion import cargar_experimento
from caoslab.informe import escribir_informe, generar_informe
from caoslab.inyectores import ErrorInyeccion, InyectorPausa
from caoslab.motor import Conclusion, ejecutar_experimento
from caoslab.sonda import SondaHTTP


def main(argv=None, crear_inyector=InyectorPausa, crear_sonda=SondaHTTP):
    argumentos = _leer_argumentos(argv)

    try:
        experimento = cargar_experimento(argumentos.archivo)
        inyector = crear_inyector(experimento.contenedor)
        if inyector.despausar_si_quedo_pausado():
            print(
                f"Aviso: el contenedor {experimento.contenedor} quedó pausado de una corrida "
                "anterior que no terminó bien. Lo despausé antes de empezar."
            )
        sonda = crear_sonda(experimento.url, experimento.peticiones_por_segundo, experimento.timeout_s)
        print(f"Experimento: {experimento.nombre}")
        resultado = ejecutar_experimento(experimento, inyector, sonda, avisar=print)
    except (ValueError, ErrorInyeccion) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except docker.errors.DockerException as error:
        print(f"Error: no pude conectarme a Docker, revisa que esté encendido.\n{error}", file=sys.stderr)
        return 2

    print()
    print(generar_informe(resultado))
    escribir_informe(resultado, argumentos.informe)
    print(f"Informe guardado en {argumentos.informe}")

    return 0 if resultado.conclusion is Conclusion.SUPERADO else 1


def _leer_argumentos(argv):
    lector = argparse.ArgumentParser(prog="caoslab", description="Experimentos de caos controlado sobre Docker.")
    comandos = lector.add_subparsers(dest="comando", required=True)
    correr = comandos.add_parser("run", help="corre un experimento descrito en un archivo YAML")
    correr.add_argument("archivo", help="ruta del experimento, por ejemplo experimento.yaml")
    correr.add_argument("--informe", default="informe.md", help="dónde guardar el informe (por defecto informe.md)")
    return lector.parse_args(argv)
