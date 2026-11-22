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

---

# Semana 7 — suite de pruebas del proyecto con IA

Funcionalidad probada: las reglas de negocio de CaosLab (estado estable,
configuración, conclusión del experimento, inyector y informe).
Asistente usado: Claude (Anthropic), en modo chat y como agente en el IDE.
Entrega relacionada: `registro_pruebas.md` y `tests/test_semana7_*.py`.

### Entrada 4 — diseño de los casos de prueba

- **Fecha:** 2026-11-22
- **Prompt o sugerencia:** «Esta es la regla de `evaluar_estado_estable()` tal como está en el contrato del README, incluida la nota del ADR-002 de que el umbral es inclusivo. Propón los casos de prueba usando particiones de equivalencia, valores límite y una tabla de decisión. Para cada caso dime de qué parte de la regla sale el esperado. No escribas código todavía y no toques mi implementación.»
- **Decisión:** Aceptada con cambios
- **Por qué:** La tabla de decisión que propuso tenía las tres condiciones correctas (muestras suficientes, tasa por encima del umbral, p95 por encima del umbral) y la simplificación de que con C1 en «no» las otras dos no importan, que es la que reduce ocho combinaciones a cinco reglas. Eso lo acepté tal cual. Lo que cambié fueron los valores límite: proponía bordes con 10 muestras, donde la tasa de error salta de 0.10 en 0.10 y no se puede poner un caso «justo en el umbral» distinto del «justo por debajo». Los rehice con 20 muestras para que 2/20 dé exactamente 0.10 y 3/20 dé 0.15, y así los tres valores del borde (debajo, exacto, encima) quedaran separados de verdad. También agregué por mi cuenta las particiones de `max_tasa_error = 0.0` y `= 1.0`, que son bordes válidos que el contrato nombra y que la propuesta se había saltado, y la fila de n = 20 del percentil, que es donde las dos fórmulas de percentil se separan.
- **Verificación:** Revisé la propuesta con las cinco preguntas de la semana. Particiones: faltaban los dos bordes válidos del presupuesto, los agregué. Límites: estaban mal elegidos por el tamaño de la muestra, los rehice. Origen del esperado: pedí que cada caso dijera de qué parte del contrato salía y verifiqué las 30 filas contra el README; las dos que no podía ubicar en ninguna fila del contrato («muestras con marca de tiempo» y «ventanas solapadas») las descarté, igual que en la semana 5. Ambigüedades: encontré dos que el contrato no resuelve (el orden de validación cuando el presupuesto y las muestras están mal a la vez, y que el rango del presupuesto no se valida al leer el YAML); las dos quedaron anotadas en la sección 1.1 del registro y una de ellas, a propósito, **sin** prueba. Reglas inventadas: ninguna que se me haya colado a la suite.
- **Commit relacionado:** `docs: tabla de casos de la semana 7 con particiones, límites y tablas de decisión`

### Entrada 5 — generación de las pruebas

- **Fecha:** 2026-11-22
- **Prompt o sugerencia:** Primero, a propósito, el prompt flojo: «Escribí las pruebas con pytest para `evaluar_estado_estable()` y `cargar_experimento()` de CaosLab», sin pasarle el contrato. Después el bueno: «Con esta regla y esta tabla de casos ya revisada, escribí las pruebas con pytest. Exijo `@pytest.mark.parametrize` con un comentario por fila que diga qué partición o qué borde es, `pytest.approx` para los decimales, `pytest.raises` con el tipo de error exacto y `match` del campo que está mal, y esperados fijos escritos a mano. No modifiques mi código.»
- **Decisión:** Aceptada con cambios
- **Por qué:** Hice los dos prompts para poder comparar, y la diferencia fue el punto de la tarea. El borrador sin contrato dio 11 pruebas: 4 eran débiles de una forma que no se nota leyendo rápido (`is not None`, `isinstance(..., float)`, `estado in (los tres estados que existen)` y un `pytest.raises(Exception)`), y 3 tenían el esperado al revés de la regla: la lista vacía lanzando error en vez de devolver `MUESTRAS_INSUFICIENTES`, el borde inclusivo abortando y el p95 interpolado al estilo de numpy. Esa última es exactamente la que me costó un defecto en la semana 5, así que el asistente repite el mismo error cuando no tiene la regla delante. Con el contrato pegado, la segunda generación salió casi derecha y lo que corregí fue forma: ids de parametrize legibles y comentarios por fila. El detalle de las 11 pruebas, con qué hice con cada una, está en la sección 2 del registro.
- **Verificación:** Apliqué las tres preguntas a cada prueba. ¿El esperado sale de la regla? Las 3 que no, las corregí contra el README, no contra lo que devolvía el código. ¿Fallaría si rompo el código? Las 4 débiles no fallaban con ninguna de las 8 mutaciones que después probé, así que las descarté; las 8 mutaciones de la sección 3 del registro son la respuesta a esta pregunta para el resto de la suite, y las 8 cayeron. ¿Cubre algo que otra prueba no cubra? Descarté lo que no agregaba ninguna fila de mis tablas. Dos pruebas del borrador fallaron pero **no** por un esperado mal puesto, sino porque encontraron defectos reales en `cargar_experimento()`: un campo numérico con texto se escapaba como `TypeError` en vez de `ErrorConfiguracion` (y el CLI solo traduce `ValueError` a código 2, así que el usuario veía un traceback), y una hipótesis en blanco pasaba la validación de campo obligatorio. Corregí el código, no las pruebas, y lo anoté como D-01 y D-02.
- **Commit relacionado:** `test: suite de la semana 7 con parametrize y tablas de decisión` y `fix: valida el tipo y los obligatorios en blanco al cargar el experimento`

### Entrada 6 — generación de los datos de prueba sintéticos

- **Fecha:** 2026-11-22
- **Prompt o sugerencia:** «Necesito datos sintéticos para los fixtures de pytest de CaosLab. El proyecto no maneja personas: consume nombres de contenedores, URLs, hipótesis y métricas. Dame cuatro experimentos inventados con contexto de negocios del Huila y que entre ellos cubran tildes, ñ y apóstrofo en el nombre del contenedor y en la URL. Nada de nombres de personas, teléfonos ni correos, ni siquiera inventados.»
- **Decisión:** Aceptada con cambios
- **Por qué:** La primera versión traía los datos difíciles solo en los nombres bonitos («caída de la réplica») y dejaba los contenedores y las URLs en ASCII limpio, que es justo donde un problema de codificación duele, porque esos dos campos viajan a Docker y a la sonda. Los reescribí para meter la ñ y el apóstrofo dentro del identificador (`inventario-ñapa-db`, `cafe-d'anita-web`) y los acentos dentro de la URL (`/menú`, `categoría=café`). También le quité una propuesta de incluir nombres de dueños de negocio: aunque fueran inventados, la regla de la tarea es no tener datos que parezcan de personas, y para probar un informe no hacen falta. Lo que agregué yo fueron los casos numéricos, que no había pedido en el prompt y no aparecieron: el cero (latencia 0 ms, `max_tasa_error` 0.0, `duracion_s` 0), los negativos y el volumen de 301 muestras con un pico aislado.
- **Verificación:** Los cuatro experimentos pasan por `cargar_experimento()` y por `generar_informe()` en `test_lee_tildes_ene_y_apostrofo_sin_romper_el_texto` y `test_el_informe_conserva_tildes_ene_y_apostrofo`, que comparan el texto leído y el texto impreso carácter por carácter contra el dato de entrada, así que si algo se corrompiera en el camino la prueba lo diría. El informe también se escribe a disco y se vuelve a leer en UTF-8 en `test_el_archivo_del_informe_se_guarda_en_utf8`. Revisé el conftest entero para confirmar que no quedó ningún nombre de persona, teléfono, correo ni documento, y que todas las URLs son `localhost`. Está anotado en la sección 4 del registro.
- **Commit relacionado:** `test: datos de prueba sintéticos con tildes, ñ, apóstrofo y volumen`
