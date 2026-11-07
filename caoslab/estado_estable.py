"""Evaluación del estado estable de un experimento de caos (HU-01).

Todavía sin implementar: las pruebas de tests/test_estado_estable.py se
escribieron primero y deben estar en rojo antes de pedir el código.
"""

from collections.abc import Sequence

from caoslab.modelos import Muestra, PresupuestoError, Veredicto


def evaluar_estado_estable(
    muestras: Sequence[Muestra],
    presupuesto: PresupuestoError,
) -> Veredicto:
    """Decide si el experimento sigue dentro del presupuesto de error."""
    raise NotImplementedError("Pendiente: implementación de la semana 5.")
