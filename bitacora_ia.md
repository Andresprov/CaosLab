# Bitácora de uso de IA

Proyecto: CaosLab — agente de pruebas de caos controlado sobre una aplicación en Docker
Estudiante: Andrés David Trujillo
Funcionalidad: HU-01 Detener el experimento cuando se agota el presupuesto de error
Asistente usado: Claude (Anthropic), en modo chat y como agente en el IDE

## Entradas

### Entrada 1

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «Este es el contrato de `evaluar_estado_estable()` del README. Propón casos de prueba de límite que se me puedan estar escapando, sin escribir todavía la implementación.»
- **Decisión:** Aceptada con cambios
- **Por qué:** De los siete casos que propuso, tomé tres que sí eran del contrato: la lista vacía, la muestra única y el pico aislado de latencia en 20 muestras. Los otros cuatro eran de un contrato distinto al mío (muestras con marca de tiempo desordenada, ventanas solapadas, muestras duplicadas y `None` en la lista); ninguno aparece en el criterio de aceptación de la HU-01 y probarlos me habría obligado a implementar comportamiento que nadie pidió. El caso del pico aislado lo reescribí yo con números que hacen visible la diferencia entre las dos formas de calcular un percentil.
- **Verificación:** Comparé cada caso propuesto contra la tabla de casos límite del README y descarté los que no correspondían a ninguna fila. Las tres pruebas que conservé fallaron al ejecutarse contra la firma sin implementar, que es lo que se esperaba en ese momento.
- **Commit relacionado:** `d2bd7ef` — test: pruebas del estado estable del experimento (en rojo)

### Entrada 2

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «El asistente propuso usar `numpy.percentile(latencias, 95)` para calcular la latencia p95.»
- **Decisión:** Rechazada
- **Por qué:** Dos razones. La primera es de dependencias: el ADR-001 del diseño de la semana 4 dice que el núcleo de CaosLab solo usa la librería estándar, porque el agente se ejecuta dentro de un contenedor que debe quedar liviano, y numpy para ordenar como máximo unos cientos de latencias por ventana no se justifica. La segunda es de comportamiento: `numpy.percentile()` interpola por omisión, así que devuelve un número que nunca se observó. Para decidir si abortar un experimento prefiero reportar una latencia que de verdad midió alguna petición, y eso es lo que dice el contrato del README.
- **Verificación:** Implementé el percentil por rango más cercano con `sorted()` y `math.ceil()`, ambos de la librería estándar, y pasaron las cuatro pruebas que tocan la latencia. Confirmé en la documentación de numpy que el método por omisión de `percentile()` es `linear`, es decir interpolado.
- **Commit relacionado:** `cbfc36a` — fix: calcula el p95 por rango más cercano (todas las pruebas en verde)

### Entrada 3

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «Implementa `evaluar_estado_estable()` respetando el contrato del README y sin modificar ninguna de las 12 pruebas de `tests/test_estado_estable.py`.»
- **Decisión:** Aceptada con cambios
- **Por qué:** La estructura general servía: validar primero, devolver temprano cuando no hay muestras suficientes, calcular las dos métricas y recoger los motivos. Pero el cálculo del percentil estaba mal, con `int(0.95 * n)` en lugar del método de rango más cercano que pide el contrato, y la prueba del pico aislado lo detectó. También cambié los mensajes de `ValueError`: el asistente los escribió en inglés y genéricos («invalid input»), y los dejé en español nombrando el dato inválido y la posición de la muestra, porque ese mensaje es lo que va a ver quien configure mal un experimento.
- **Verificación:** `pytest` sobre la versión del asistente: 11 pasan y 1 falla. Dejé ese estado en un commit propio para que quede el registro de que la prueba atrapó el defecto, y lo corregí en el commit siguiente, donde las 12 pasan.
- **Commit relacionado:** `e92c145` (11 pasan, 1 falla) y `cbfc36a` (12 pasan)

### Entrada 4

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «La prueba del pico aislado falla: con 20 muestras el p95 devuelve 5000 ms en vez de 100 ms. Explícame por qué y corrígelo sin tocar la prueba.»
- **Decisión:** Aceptada
- **Por qué:** La explicación coincidía con lo que yo había razonado leyendo el error: `int(0.95 * 20)` da 19, que en una lista de 20 elementos es el último, mientras que el rango más cercano es `ceil(0.95 * 20) - 1 = 18`, la posición 19 de 20. La consecuencia en producción es seria: una sola petición lenta de veinte habría abortado un experimento que el sistema estaba aguantando bien, y el equipo habría perdido la ventana de observación. La corrección es de una línea y es exactamente la fórmula que ya estaba escrita en el contrato del README, así que la acepté tal cual.
- **Verificación:** `pytest` pasa de 11 a 12 en verde. Además verifiqué a mano los índices para n = 1, n = 10 y n = 20 con las dos fórmulas, y comprobé que las otras tres pruebas de latencia seguían pasando, para confirmar que no había arreglado un caso rompiendo otro.
- **Commit relacionado:** `cbfc36a` — fix: calcula el p95 por rango más cercano (todas las pruebas en verde)

### Entrada 5

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «Con las 12 pruebas en verde, propón un refactor de `evaluar_estado_estable()`. No cambies el comportamiento ni las pruebas.»
- **Decisión:** Aceptada con cambios
- **Por qué:** Acepté dividir la función de 60 líneas en auxiliares con un solo propósito y sacar los valores mágicos a las constantes `PERCENTIL_LATENCIA` y `SIN_EVIDENCIA`, porque la función hacía cuatro cosas a la vez y costaba leerla. Agregué por mi cuenta que `_percentil_por_rango_mas_cercano()` reciba el percentil como parámetro en vez de fijarlo adentro, para poder reutilizarla en el p99 que pide la HU-04 del backlog. Y rechacé una parte: el asistente proponía mover las validaciones a los `__post_init__` de las dataclasses. Eso cambia dónde se lanza el `ValueError` (al construir el presupuesto, no al evaluar) y habría roto las tres pruebas de error, que es justo lo que el enunciado prohíbe.
- **Verificación:** `pytest` sigue en 12 en verde. Comprobé con `git diff d2bd7ef HEAD -- tests/` que el directorio de pruebas no tiene ni un cambio desde el commit en rojo.
- **Commit relacionado:** `6f2c864` — refactor: separa validación, métricas y motivos en el estado estable

### Entrada 6

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** «Para que la prueba del pico aislado pase, puedo cambiar el umbral esperado de 100.0 a 5000.0, que es lo que devuelve la implementación.»
- **Decisión:** Rechazada
- **Por qué:** Esto lo consideré yo antes de entender el error, y lo descarto por escrito porque es exactamente la trampa que advierte el enunciado. La prueba no estaba mal: el valor 100.0 sale del contrato del README, que se escribió antes del código. Ajustar la expectativa al resultado del código habría dejado las 12 en verde escondiendo un defecto real, y el agente abortaría experimentos sanos en cuanto una petición de veinte se demorara. La prueba era la que tenía razón; el código era el que estaba mal.
- **Verificación:** No modifiqué la prueba. Corregí la implementación y las 12 pasaron igual. El historial lo respalda: `git diff d2bd7ef HEAD -- tests/` no devuelve ningún cambio.
- **Commit relacionado:** ninguno, por eso mismo: no hay commit que toque `tests/` después de `d2bd7ef`

## Resumen

| Decisión | Cantidad |
|---|---|
| Aceptadas | 1 |
| Aceptadas con cambios | 3 |
| Rechazadas | 2 |

## Errores que atraparon las pruebas

Falló `test_un_pico_aislado_de_latencia_en_veinte_muestras_no_mueve_el_p95`, con
`AssertionError: assert 5000.0 == 100.0`.

El asistente calculó el percentil 95 como `int(0.95 * len(latencias))`. Con 20
muestras eso da el índice 19, que en una lista de 20 elementos ordenados es el
último, así que el p95 terminaba siendo la muestra más lenta de todas. En la
prueba, 19 muestras de 100 ms y un pico de 5000 ms daban un p95 de 5000 ms y el
veredicto era `ABORTAR` cuando el contrato dice `CONTINUAR`.

Las otras once pruebas pasaban porque con 1, 3 y 10 muestras las dos fórmulas
coinciden por casualidad: con n = 10, `int(9.5) = 9` y `ceil(9.5) - 1 = 9`. La
diferencia solo aparece cuando `0.95 * n` da un número entero, y el primer caso
así es n = 20. Si no hubiera escrito esa prueba de límite, el defecto habría
llegado a producción escondido detrás de once pruebas en verde.

Lo corregí con `math.ceil(PERCENTIL_LATENCIA * len(ordenados)) - 1`, que es el
método de rango más cercano documentado en el contrato del README, en el commit
`cbfc36a`. No modifiqué la prueba.

## Reflexión final

Donde más me ayudó el asistente fue en la velocidad de la primera versión: la
estructura de validar, salir temprano, calcular y decidir me la dio en un minuto
y era razonable. Donde no me sirvió fue en las decisiones: propuso numpy contra
una decisión de diseño que ya estaba escrita en el ADR-001, inventó casos de
prueba de un contrato que no era el mío, y el único cálculo con algo de sutileza,
el percentil, lo hizo mal.

Mis pruebas atraparon ese error de percentil, que era el más peligroso de todos
porque solo aparece cuando `0.95 * n` da un entero y las otras once pruebas lo
tapaban. Escribir el contrato antes fue lo que lo hizo posible: cuando la prueba
falló, tenía un documento que decía cuál era el valor correcto, y no tuve que
decidir si creerle al código o a la prueba.

La próxima vez voy a pegar el contrato completo en el prompt desde el primer
mensaje y no solo la firma, porque la mitad de lo que tuve que corregir eran
cosas que el contrato ya resolvía. Y voy a pedirle al asistente que me explique
el cálculo antes de aceptarlo, no después de que falle una prueba.
