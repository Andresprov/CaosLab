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

## Entradas de la semana 6: revisión de código y seguridad

### Entrada 7

- **Fecha:** 2026-11-14
- **Prompt o sugerencia:** «Rol: eres un revisor de código senior especializado en seguridad de aplicaciones Python. […] Revisa con estos criterios, en orden: inyección, secretos y configuración, contraseñas, control de acceso, dependencias, errores probables y legibilidad. Devuelve una tabla Archivo:línea | Problema | Categoría OWASP | Severidad | Corrección, y separa lo que puedes asegurar de las sospechas.» (El prompt completo está en `revision_seguridad.md`, sección 3.)
- **Decisión:** Aceptada con cambios
- **Por qué:** De 13 hallazgos, 8 eran reales y 5 falsos positivos. Los falsos positivos fueron la carrera sobre `_muestras` (ya está protegida con el candado), la inyección SQL en el `INSERT` (ya usa parámetros), `yaml.load` (el código usa `safe_load`), el informe que diría «revertido» si falla la inyección (ese caso nunca llega al informe) y el `KeyError` de `URL_BD` (es intencional). La IA no vio lo más grave: las 14 vulnerabilidades de starlette, que solo aparecieron con `pip-audit`, ni el `.gitignore` que ignoraba `.env.example`.
- **Verificación:** Cada hallazgo lo comprobé ejecutando el código, no leyéndolo. Un script cargó un YAML con `duracion_s: "treinta"` (salió `TypeError`), con `https://example.com/`, con `file:///etc/passwd` y con `postgres-produccion` (los tres cargaron sin error), y creó una sonda con 100000 peticiones por segundo (pool de 200002 hilos). Los falsos positivos los descarté señalando la línea que los desmiente.
- **Commit relacionado:** los trece commits de corrección, refactor y documentación, de `885ae5d` a `126bb05`; la tabla con cada uno está en `revision_seguridad.md`

### Entrada 8

- **Fecha:** 2026-11-14
- **Prompt o sugerencia:** «Corrige H-02: que `InyectorPausa` no acepte contenedores cuyo nombre no empiece por `caoslab-`, y agrega pruebas de abuso. No modifiques las pruebas existentes.»
- **Decisión:** Aceptada con cambios
- **Por qué:** La primera versión validaba el nombre en el constructor de `InyectorPausa`. Eso rompió `test_avisa_con_claridad_si_el_contenedor_no_existe`, que crea un inyector para el contenedor `no-existe` y espera el mensaje «no existe el contenedor». Cambiar esa prueba habría sido justo lo que prohíbe el enunciado, así que se cambió el código: la validación pasó a `_buscar()`, después de comprobar que el contenedor existe. Así se conserva el mensaje original y la protección cubre `inyectar()` y `despausar_si_quedo_pausado()`. La primera barrera sigue en `cargar_experimento`, para que el CLI falle con código 2 antes de tocar Docker.
- **Verificación:** `pytest` pasó de 1 prueba fallida a 71 en verde. `git diff caef884 -- tests/` muestra que en `tests/` solo se agregaron pruebas; la única línea quitada es el formato de una llamada en `test_informe.py` (E501), que conserva la misma aserción.
- **Commit relacionado:** `4227d7a` — fix(seguridad): solo se inyectan fallos en contenedores caoslab-*

### Entrada 9

- **Fecha:** 2026-11-14
- **Prompt o sugerencia:** Le di a un agente de código (Claude Code) esta instrucción delimitada: «Trabaja solo en la rama `semana-6-revision`. Configura ruff con E, F, B y S, corrige los hallazgos reales de `revision_seguridad.md`, un commit por corrección con un mensaje que diga qué se corrigió, agrega docstrings y el README de ocho secciones. No modifiques las aserciones de las pruebas existentes, no toques `main` y no subas `.env`.»
- **Decisión:** Aceptada tras revisar el diff
- **Por qué:** El agente hizo los cambios en su propia rama y los dejó en el pull request #1, sin tocar `main`. Lo integré solo después de leer el diff completo en GitHub, commit por commit, y de comprobar que ningún cambio en `tests/` afloja una aserción.
- **Verificación:** El agente corrió en una carpeta limpia `pip install -r requirements.txt`, `pytest -m "not integracion"` (75 en verde), `ruff check .` (sin avisos) y `pip-audit` (sin vulnerabilidades). Docker no estaba disponible en su entorno, así que las 3 pruebas de integración las corrí yo con Docker encendido antes de integrar.
- **Commit relacionado:** pull request #1 (`semana-6-revision` → `main`)

## Entradas de la entrega 1: el resto del agente (21 commits)

Estos 21 commits, de `7d843c1` a `caef884`, se hicieron el 2026-11-07 con
Claude Code como agente, después de cerrar la HU-01. Todos llevan
`Co-Authored-By: Claude` en el mensaje del commit.

### Entrada 10

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí al agente que preparara la estructura del proyecto para poder instalarlo y ejecutarlo correctamente, separando la documentación de los módulos y configurando las dependencias, los requisitos de Python y el comando de consola.
- **Qué hizo la IA:** Sacó los docstrings de `modelos.py` y `estado_estable.py` a `DOCUMENTACION.txt` sin cambiar la lógica, y creó el `pyproject.toml` con el comando `caoslab`, el marcador `integracion`, PyYAML, el SDK de Docker y Python 3.11 como mínimo.
- **Decisión:** Aceptada
- **Por qué:** PyYAML era necesario para leer la configuración de los experimentos en YAML, mientras que el SDK de Docker permitía interactuar programáticamente con los contenedores. Separar los docstrings en un archivo de documentación ayudaba a mantener los módulos más limpios sin perder la explicación de su funcionamiento. También era necesario definir una versión mínima de Python y facilitar la ejecución mediante el comando `caoslab`.
- **Verificación:** Revisé los archivos de configuración y documentación creados, y comprobé que las 12 pruebas de la HU-01 siguieron en verde después del refactor.
- **Commits relacionados:** `7d843c1`, `65873b3`

### Entrada 11

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que creara una aplicación de demostración para probar el comportamiento del sistema ante fallos, usando FastAPI, PostgreSQL y Docker Compose, incluyendo endpoints que permitieran diferenciar entre un servicio independiente de la base de datos y otro que dependiera de ella.
- **Qué hizo la IA:** Creó la app demo con FastAPI y PostgreSQL en `docker-compose.yml`. `/health` no toca la base de datos; `/pedidos` sí, y usa `connect_timeout` para responder 503 en vez de colgarse cuando la base está pausada.
- **Decisión:** Aceptada
- **Por qué:** Se necesitaba un entorno reproducible para probar los experimentos de caos. Tener un endpoint independiente de PostgreSQL y otro que dependiera de ella permitía comprobar que el inyector generara el fallo esperado y que el sistema detectara correctamente los servicios afectados. El `connect_timeout` evitaba que las peticiones quedaran esperando indefinidamente cuando la base de datos no respondiera.
- **Verificación:** Revisé la estructura de la aplicación y el comportamiento esperado de ambos endpoints. La verificación con Docker real se dejó para las pruebas de integración. La configuración de autenticación `trust` utilizada inicialmente en PostgreSQL se reemplazó posteriormente por una contraseña almacenada en `.env` durante la semana 6 (`eb668a7`).
- **Commit relacionado:** `26d4426`

### Entrada 12

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que implementara la carga y validación inicial del archivo de configuración del experimento `experimento.yaml`, definiendo los campos obligatorios y los valores permitidos, y que primero escribiera las pruebas para comprobar el comportamiento esperado.
- **Qué hizo la IA:** Escribió primero las pruebas de la configuración (en rojo) y después `cargar_experimento`, que lee `experimento.yaml`. Los campos obligatorios son la hipótesis, `objetivo.url`, `objetivo.contenedor`, `fallo.tipo`, `duracion_s` y el presupuesto; el único fallo aceptado es `pausar`.
- **Decisión:** Aceptada con cambios
- **Por qué:** Se necesitaba que los experimentos tuvieran una configuración definida y consistente para evitar errores al ejecutarlos. Se aceptó el enfoque de escribir primero las pruebas y después la implementación, pero la validación inicial no cubría completamente los tipos de datos ni los límites de los valores, por lo que se dejaron esos ajustes pendientes para la semana 6.
- **Verificación:** Las pruebas pasaron de rojo a verde. La validación de tipos y límites quedó incompleta y se corrigió en la semana 6 (`89430fc`).
- **Commits relacionados:** `8672459` (en rojo), `ca8a4ea` (en verde)

### Entrada 13

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que diseñara el mecanismo de inyección de fallos mediante Docker, definiendo una interfaz común para los inyectores y desarrollando el primer inyector de pausa de contenedores, junto con sus pruebas.
- **Qué hizo la IA:** Escribió las pruebas del inyector (en rojo) y el `InyectorPausa` con el SDK de Docker. `Inyector` es un `Protocol` con `inyectar()` y `revertir()`, así el motor no depende de un fallo concreto. `revertir()` solo despausa si este inyector pausó y se puede llamar varias veces; `despausar_si_quedo_pausado()` recupera un contenedor que quedó pausado si el proceso murió.
- **Decisión:** Aceptada con cambios
- **Por qué:** El uso de un `Protocol` permitía definir un contrato común entre el motor y los distintos tipos de inyectores, sin acoplar el proyecto a una única implementación. Se aceptó el inyector de pausa y su mecanismo de reversión, aunque posteriormente fue necesario reforzar la seguridad para restringir las acciones a contenedores creados para los experimentos de CaosLab.
- **Verificación:** Las pruebas pasaron de rojo a verde. La restricción a contenedores `caoslab-*` no estaba implementada inicialmente y se agregó en la semana 6 (`4227d7a`).
- **Commits relacionados:** `e85dc2b` (en rojo), `4a1fb81` (en verde)

### Entrada 14

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que implementara la reversión de los fallos de manera segura, garantizando que los contenedores recuperaran su estado incluso ante excepciones, interrupciones del usuario o errores durante la inyección, y que desarrollara pruebas para esos escenarios.
- **Qué hizo la IA:** Escribió las pruebas de la reversión garantizada (excepción a mitad del experimento, `KeyboardInterrupt`, Ctrl+C durante la línea base y durante el fallo, falla al inyectar, y el manejador de SIGINT restaurado al terminar) con un inyector y una sonda falsos, sin Docker. Después puso `inyector.revertir()` en un `finally` y capturó SIGINT, SIGTERM y SIGBREAK para que marquen una parada ordenada en vez de matar el proceso.
- **Decisión:** Aceptada
- **Por qué:** La recuperación del sistema después de un experimento era una prioridad, ya que un fallo inyectado no debía dejar los contenedores en un estado alterado. El uso de `finally` aseguraba que la reversión se intentara incluso cuando ocurrían excepciones, y el manejo de señales permitía finalizar el experimento de forma controlada.
- **Verificación:** Las 7 pruebas de `test_reversion.py` pasaron de rojo a verde. La reversión quedó cubierta mediante pruebas automatizadas con objetos falsos, aunque no se registró una prueba manual de Ctrl+C contra Docker real.
- **Commits relacionados:** `e5ca36d` (en rojo), `11e5059` (en verde)

### Entrada 15

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que desarrollara la sonda HTTP para medir el comportamiento del servicio durante los experimentos, usando pruebas contra un servidor local y sin añadir dependencias externas, respetando lo establecido en el ADR-001.
- **Qué hizo la IA:** Escribió las pruebas de la sonda contra un servidor HTTP local (en rojo) y la `SondaHTTP`: un hilo marca el ritmo y un pool de hilos hace las peticiones, para que una petición lenta no baje el número de muestras cuando el servicio se cuelga. Solo usa `urllib`, de acuerdo con el ADR-001.
- **Decisión:** Aceptada
- **Por qué:** La sonda debía mantener mediciones periódicas y confiables, incluso cuando el endpoint respondiera lentamente. Separar la planificación de las mediciones de las peticiones mediante hilos ayudaba a mantener el ritmo de muestreo. Se decidió utilizar `urllib` para evitar agregar dependencias innecesarias y cumplir con la decisión arquitectónica del ADR-001.
- **Verificación:** Las 8 pruebas de `test_sonda.py` pasaron de rojo a verde, incluida la prueba que comprobaba que el ritmo de muestreo se mantuviera frente a un endpoint que tardaba 1 segundo en responder.
- **Commits relacionados:** `08c142d` (en rojo), `a98e6d6` (en verde)

### Entrada 16

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que implementara el motor de ejecución de experimentos, integrando la línea base, la inyección del fallo, el monitoreo por ventanas y la evaluación del estado estable, con pruebas para verificar los distintos resultados posibles.
- **Qué hizo la IA:** Escribió 8 pruebas del motor (4 en rojo; las otras 4 ya las cumplía el esqueleto de la reversión) y la implementación: cada ventana se evalúa con `evaluar_estado_estable()` sin cambios, si la línea base no da `CONTINUAR` no se inyecta nada, y si ninguna ventana junta evidencia el resultado es `SIN_EVIDENCIA`. Luego refactorizó `_esperar` para calcular el límite con `time.monotonic()` en vez de restar 0.2 s por vuelta, que acumulaba error.
- **Decisión:** Aceptada con cambios
- **Por qué:** El motor debía seguir una secuencia controlada de línea base, inyección y evaluación, evitando ejecutar fallos cuando el sistema ya presentaba condiciones inestables. Se aceptó la lógica de evaluación y los resultados definidos, pero se ajustó el método de espera para utilizar tiempo monotónico, evitando errores de acumulación y mejorando la precisión temporal del experimento.
- **Verificación:** Las pruebas del motor pasaron de rojo a verde y continuaron pasando después del refactor de `_esperar`.
- **Commits relacionados:** `b7580f2` (en rojo), `e67c7b0` (en verde), `68140ce` (refactor)

### Entrada 17

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que desarrollara la generación del informe de resultados en Markdown y el comando de consola `caoslab run`, incluyendo los códigos de salida, el manejo de errores de configuración y Docker, y la visualización del progreso de ejecución.
- **Qué hizo la IA:** Escribió las pruebas y la implementación del informe en markdown (hipótesis, línea base, ventanas y veredicto) y del comando `caoslab run`, con códigos de salida 0 (superado), 1 (cualquier otro final) y 2 (configuración inválida o Docker sin responder). Después corrigió el CLI para escribir en UTF-8 y mostrar el progreso al instante.
- **Decisión:** Aceptada con cambios
- **Por qué:** El informe permitía documentar y analizar los resultados de cada experimento de forma legible, mientras que el comando CLI facilitaba su ejecución sin tener que utilizar directamente los módulos internos. Se aceptó la implementación inicial, pero fue necesario corregir la codificación de salida y la actualización del progreso para que funcionaran correctamente en Windows al redirigir la salida de consola.
- **Verificación:** Las pruebas pasaron de rojo a verde. Durante la verificación con Docker real y salida redirigida, se detectaron problemas de codificación UTF-8 y de progreso retrasado que no habían sido cubiertos por las pruebas automatizadas, y se corrigieron posteriormente (`b2648da`).
- **Commits relacionados:** `4294328` y `7185c4f` (informe), `ea21db2` y `84c4365` (CLI), `b2648da` (corrección)

### Entrada 18

- **Fecha:** 2026-11-07
- **Prompt o sugerencia:** Le pedí que preparara las pruebas de integración de la aplicación demo con Docker, verificando el comportamiento del experimento cuando se pausaba PostgreSQL y cuando se ejecutaba sobre un endpoint independiente de la base de datos, además de completar el README y la documentación de los módulos.
- **Qué hizo la IA:** Escribió dos pruebas de extremo a extremo, marcadas como `integracion`: una pausa la base y comprueba que el experimento sobre `/pedidos` aborta, y la otra comprueba que `/health` lo supera; en ambas la base termina corriendo. También escribió el README de la entrega 1 y la documentación de cada módulo en `DOCUMENTACION.txt`.
- **Decisión:** Aceptada
- **Por qué:** Las pruebas de integración permitían validar el funcionamiento del sistema en un escenario más cercano al real, verificando tanto la detección de fallos como la recuperación del servicio. El README y la documentación facilitaban la instalación, ejecución y comprensión del proyecto para otros usuarios.
- **Verificación:** Revisé el README y la documentación generada, así como la estructura de las pruebas de integración y sus comprobaciones de recuperación de PostgreSQL. La ejecución de estas pruebas dependía de tener Docker disponible y operativo.
- **Commits relacionados:** `8393fdb`, `caef884`

## Resumen

| Decisión | Cantidad |
|---|---|
| Aceptadas | 7 |
| Aceptadas con cambios | 9 |
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
