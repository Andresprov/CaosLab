"""Guion de la semana 7: aplica una mutación a la vez, corre la suite y deshace el cambio.

Uso: python herramientas/mutar.py  (desde la raíz del repositorio)
Los resultados de cada mutación están en registro_pruebas.md, sección 3.
"""
import pathlib
import subprocess
import sys

MUTACIONES = [
    ("M1", "caoslab/estado_estable.py",
     "    if tasa_error > presupuesto.max_tasa_error:",
     "    if tasa_error >= presupuesto.max_tasa_error:",
     "umbral de tasa de error: > por >="),
    ("M2", "caoslab/estado_estable.py",
     "    indice = math.ceil(percentil * len(ordenados)) - 1",
     "    indice = int(percentil * len(ordenados))",
     "p95: rango mas cercano por truncamiento"),
    ("M3", "caoslab/estado_estable.py",
     "    if len(muestras) < presupuesto.minimo_muestras:",
     "    if len(muestras) <= presupuesto.minimo_muestras:",
     "minimo de muestras: < por <="),
    ("M4", "caoslab/estado_estable.py",
     "    if latencia_p95_ms > presupuesto.max_latencia_p95_ms:",
     "    if latencia_p95_ms > presupuesto.max_latencia_p95_ms * 1.1:",
     "umbral de latencia: 10% de holgura regalada"),
    ("M5", "caoslab/motor.py",
     "    total = math.ceil(experimento.duracion_s / experimento.ventana_s)",
     "    total = int(experimento.duracion_s / experimento.ventana_s)",
     "numero de ventanas: ceil por int"),
    ("M6", "caoslab/inyectores.py",
     "        contenedor = self._buscar()\n"
     "        if contenedor.status == \"paused\":\n            contenedor.unpause()",
     "        contenedor = self._buscar()\n        contenedor.unpause()",
     "revertir: despausa sin revisar el estado"),
    ("M7", "caoslab/informe.py",
     '    return f"{fraccion * 100:.2f} %"',
     '    return f"{fraccion * 100:.0f} %"',
     "informe: porcentaje con 0 decimales"),
    ("M8", "caoslab/configuracion.py",
     "        if getattr(experimento, campo) <= 0:",
     "        if getattr(experimento, campo) < 0:",
     "campos positivos: <= 0 por < 0"),
]

for codigo, archivo, viejo, nuevo, descripcion in MUTACIONES:
    ruta = pathlib.Path(archivo)
    original = ruta.read_text(encoding="utf-8")
    if viejo not in original:
        raise SystemExit(f"{codigo}: no encontre el fragmento")
    ruta.write_text(original.replace(viejo, nuevo, 1), encoding="utf-8")
    salida = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "not integracion", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True,
    ).stdout
    lineas = salida.splitlines()
    fallidas = [linea.split(" ")[1] for linea in lineas if linea.startswith("FAILED")]
    resumen = [linea for linea in lineas if "passed" in linea or "failed" in linea][-1]
    ruta.write_text(original, encoding="utf-8")
    print(f"### {codigo} | {archivo} | {descripcion}")
    print(f"    {resumen.strip()}")
    for f in fallidas[:6]:
        print(f"    - {f}")
    print(f"    (total fallidas: {len(fallidas)})")
