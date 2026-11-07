from pathlib import Path

from caoslab.modelos import Estado
from caoslab.motor import Conclusion


def generar_informe(resultado):
    experimento = resultado.experimento
    presupuesto = experimento.presupuesto
    lineas = [
        f"# Informe del experimento: {experimento.nombre}",
        "",
        "## Hipótesis",
        "",
        experimento.hipotesis,
        "",
        "## Configuración",
        "",
        f"- Objetivo: {experimento.url}",
        f"- Fallo: {experimento.tipo_fallo} el contenedor {experimento.contenedor}",
        f"- Duración: {experimento.duracion_s:g} s en ventanas de {experimento.ventana_s:g} s",
        f"- Sonda: {experimento.peticiones_por_segundo:g} peticiones por segundo, timeout de {experimento.timeout_s:g} s",
        f"- Presupuesto: tasa de error máxima {_porcentaje(presupuesto.max_tasa_error)}, "
        f"p95 máximo {presupuesto.max_latencia_p95_ms:g} ms, "
        f"mínimo {presupuesto.minimo_muestras} muestras por ventana",
        "",
        "## Línea base",
        "",
        _linea_base(resultado),
        "",
        "## Durante el fallo",
        "",
        *_tabla_de_ventanas(resultado),
        "",
        "## Veredicto",
        "",
        f"**{resultado.conclusion.value}**: {_explicacion(resultado)}",
        "",
    ]

    motivos = _motivos(resultado)
    if motivos:
        lineas += ["Motivos:", "", *[f"- {motivo}" for motivo in motivos], ""]

    if resultado.fallo_inyectado:
        lineas.append("Fallo revertido: el contenedor volvió a su estado original.")
    else:
        lineas.append("No se inyectó ningún fallo, así que no hubo nada que revertir.")

    return "\n".join(lineas) + "\n"


def escribir_informe(resultado, ruta):
    Path(ruta).write_text(generar_informe(resultado), encoding="utf-8")


def _porcentaje(fraccion):
    return f"{fraccion * 100:.2f} %"


def _linea_base(resultado):
    base = resultado.linea_base
    if base is None:
        return "No se alcanzó a medir."
    return (
        f"{resultado.muestras_linea_base} muestras, tasa de error {_porcentaje(base.tasa_error)}, "
        f"p95 {base.latencia_p95_ms:.1f} ms ({base.estado.value})"
    )


def _tabla_de_ventanas(resultado):
    if not resultado.fallo_inyectado:
        return ["El fallo no se llegó a inyectar."]
    if not resultado.ventanas:
        return ["No alcanzó a evaluarse ninguna ventana."]
    filas = [
        "| Ventana | Muestras | Tasa de error | p95 | Estado |",
        "|---|---|---|---|---|",
    ]
    for ventana in resultado.ventanas:
        v = ventana.veredicto
        filas.append(
            f"| {ventana.numero} | {ventana.muestras} | {_porcentaje(v.tasa_error)} | "
            f"{v.latencia_p95_ms:.1f} ms | {v.estado.value} |"
        )
    return filas


def _explicacion(resultado):
    conclusion = resultado.conclusion
    if conclusion is Conclusion.SUPERADO:
        return "la hipótesis se sostiene, el sistema se mantuvo dentro del presupuesto durante todo el fallo."
    if conclusion is Conclusion.ABORTADO:
        numero = resultado.ventanas[-1].numero
        return f"la hipótesis no se sostiene, en la ventana {numero} se agotó el presupuesto y el experimento se detuvo."
    if conclusion is Conclusion.LINEA_BASE_INESTABLE:
        return "no se inyectó el fallo porque el sistema no estaba estable antes de empezar."
    if conclusion is Conclusion.SIN_EVIDENCIA:
        return "no se puede concluir nada, ninguna ventana juntó las muestras mínimas."
    return "el experimento se interrumpió antes de terminar."


def _motivos(resultado):
    if resultado.conclusion is Conclusion.ABORTADO:
        return list(resultado.ventanas[-1].veredicto.motivos)
    if resultado.conclusion is Conclusion.LINEA_BASE_INESTABLE:
        base = resultado.linea_base
        if base.estado is Estado.MUESTRAS_INSUFICIENTES:
            return [
                f"la línea base solo juntó {resultado.muestras_linea_base} muestras "
                f"y el mínimo es {resultado.experimento.presupuesto.minimo_muestras}"
            ]
        return list(base.motivos)
    return []
