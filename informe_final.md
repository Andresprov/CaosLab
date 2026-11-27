# Informe final del proyecto integrador

Proyecto: CaosLab, agente de pruebas de caos controlado sobre una aplicación en Docker
Estudiante: Andrés David Trujillo
Repositorio: https://github.com/Andresprov/CaosLab
Fecha: 2026-11-27

> Este informe lo llenamos entre los dos, Claude Code (agente) y yo. El agente
> lo redactó a partir del repositorio y de lo que yo había escrito en la
> bitácora (las entradas 1 a 21 y la reflexión final); yo lo revisé y ajusté
> antes de entregarlo. Registro en la [bitácora, entrada 22](bitacora_ia.md).

## 1. Resumen

Los equipos que operan aplicaciones en contenedores no saben cómo se comportan
cuando falla una dependencia hasta que el fallo ocurre en producción. CaosLab
mide la línea base de una aplicación, le inyecta un fallo controlado (pausar un
contenedor), vigila la salud del sistema por ventanas de tiempo y detiene el
experimento en cuanto el daño supera el presupuesto de error aceptado. El fallo
siempre se revierte y queda un informe en markdown. Usé IA (Claude) en los
requisitos, el diseño, el código, las pruebas, la revisión de seguridad, la
documentación y la redacción de este informe. La verificación se apoyó en
pruebas escritas antes del código: 234 pruebas unitarias y 3 de integración
pasan en el pipeline de GitHub Actions, ruff y pip-audit quedan limpios, ocho
mutaciones introducidas a propósito fueron detectadas y las pruebas atraparon un error de la
IA en el cálculo del p95 que habría abortado experimentos sanos.

## 2. Problema y usuario

**Quién tiene el problema.** Los equipos que desarrollan y operan aplicaciones
en contenedores Docker, en particular servicios que dependen de una base de
datos. Necesitan saber, antes de que pase en producción, si su aplicación
aguanta que una dependencia deje de responder.

**Cómo se resolvía antes.** Esperando al incidente real, o provocando el fallo
a mano (por ejemplo con `docker pause`) y mirando los registros. Las dos formas
tienen el mismo problema: no hay un criterio escrito de cuándo parar, nadie
garantiza que el fallo se revierta si algo sale mal y no queda evidencia
comparable entre una prueba y otra.

**Qué necesita.** Una herramienta que mida la línea base, inyecte un fallo
controlado, se detenga sola cuando el daño supera un presupuesto de error que
el equipo fijó antes (la HU-01), revierta el fallo pase lo que pase y deje un
informe que explique la decisión. Además, que no pueda usarse contra sistemas
ajenos: solo trabaja sobre la copia local.

## 3. La IA en el ciclo de vida

| Módulo y fase | Qué hice con IA | Herramienta | Evidencia (enlace) | Cómo verifiqué |
|---|---|---|---|---|
| 1. Fundamentos | Definir el problema, el alcance de la herramienta y los límites de seguridad de un agente de caos | Claude (chat) | Propuesta del módulo 1 | Contrasté la propuesta con el enunciado del proyecto integrador |
| 2. Requisitos | Pedí casos de prueba de límite para el contrato de la HU-01; acepté 3 de 7 y descarté 4 que eran de otro contrato. | Claude (chat) | [docs/contrato_hu01.md](docs/contrato_hu01.md), [bitácora, entrada 1](bitacora_ia.md) | Comparé cada caso con la tabla de casos límite del contrato |
| 3. Diseño | La IA propuso `numpy.percentile()`; lo rechacé por el ADR-001 (solo librería estándar). | Claude (chat) | [bitácora, entrada 2](bitacora_ia.md), ADR-001 (módulo 3) | Comparé contra el ADR-001 y la documentación de numpy |
| 4. Código | La IA implementó `evaluar_estado_estable()` y, como agente, el inyector, la reversión, la sonda, el motor, el informe y el CLI; yo corregí y ajusté lo que generó | Claude (chat) y Claude Code (agente) | [bitácora, entradas 3 a 5 y 10 a 17](bitacora_ia.md), [caoslab/](caoslab/) | Pruebas escritas antes del código (commits en rojo y en verde) |
| 5. Pruebas | Pruebas unitarias, de reversión con dobles en memoria, de abuso y de extremo a extremo con Docker; en la semana 7, una suite con particiones de equivalencia, valores límite, tablas de decisión y datos sintéticos | Claude Code (agente) y Claude (chat) | [tests/](tests/), [registro_pruebas.md](registro_pruebas.md), [bitácora, entradas 18 a 21](bitacora_ia.md) | `pytest`: 234 unitarias y 3 de integración en verde; ninguna aserción se cambió para que pasara; 8 de 8 mutaciones detectadas con [herramientas/mutar.py](herramientas/mutar.py) |
| 6. Operación | Revisión de seguridad con IA, correcciones en rama propia y pull request; despliegue de la app demo con Docker Compose; pipeline de integración continua | Claude (chat), Claude Code, ruff, pip-audit, GitHub Actions | [revision_seguridad.md](revision_seguridad.md), [docker-compose.yml](docker-compose.yml), [ci.yml](.github/workflows/ci.yml), [bitácora, entradas 7 a 9 y 23](bitacora_ia.md) | Cada hallazgo se comprobó ejecutando el código; pip-audit encontró lo que la IA no vio |

## 4. Verificación: lo que la IA hizo mal y cómo lo encontré

### Caso 1: el p95 calculado con el índice equivocado

- **Fase:** código
- **Qué propuso la IA:** calcular el percentil 95 como `int(0.95 * len(latencias))`.
- **Qué estaba mal:** con 20 muestras el índice es 19, el último de la lista, así que el p95 era la muestra más lenta. Con 19 muestras de 100 ms y un pico de 5000 ms el veredicto era `ABORTAR` cuando el contrato dice `CONTINUAR`: un experimento sano se habría detenido por una sola petición lenta. Las otras 11 pruebas no lo notaban porque con 1, 3 y 10 muestras las dos fórmulas coinciden.
- **Cómo lo detecté:** la prueba de límite `test_un_pico_aislado_de_latencia_en_veinte_muestras_no_mueve_el_p95`, escrita antes del código a partir del contrato, falló con `assert 5000.0 == 100.0`.
- **Qué hice:** corregí el código, no la prueba, con el método de rango más cercano del contrato: `math.ceil(0.95 * n) - 1`. Commit con la prueba fallando: [`e92c145`](https://github.com/Andresprov/CaosLab/commit/e92c145); corrección: [`cbfc36a`](https://github.com/Andresprov/CaosLab/commit/cbfc36a).

### Caso 2: una dependencia que contradecía el diseño

- **Fase:** diseño
- **Qué propuso la IA:** usar `numpy.percentile(latencias, 95)`.
- **Qué estaba mal:** el ADR-001 fija que el núcleo de CaosLab solo usa la librería estándar, porque corre en un contenedor liviano. Además `numpy.percentile()` interpola por omisión y devuelve una latencia que ninguna petición tuvo, cuando el contrato pide una latencia observada.
- **Cómo lo detecté:** revisión contra el ADR-001 y contra la documentación de numpy, que confirma que el método por omisión es `linear`.
- **Qué hice:** rechacé la sugerencia e implementé el percentil con `sorted()` y `math.ceil()`. Registro: [bitácora, entrada 2](bitacora_ia.md); commit: [`cbfc36a`](https://github.com/Andresprov/CaosLab/commit/cbfc36a).

### Caso 3: una revisión de seguridad con falsos positivos y huecos

- **Fase:** operación
- **Qué propuso la IA:** 13 hallazgos de seguridad sobre el commit `caef884`.
- **Qué estaba mal:** 5 eran falsos positivos (una carrera sobre `_muestras` que ya tenía candado, una inyección SQL en una consulta que ya usaba parámetros, `yaml.load` cuando el código usa `safe_load`, entre otros). Y no vio lo más grave: 14 vulnerabilidades conocidas en starlette, la dependencia de FastAPI de la app demo, ni el `.gitignore` que impedía subir `.env.example`.
- **Cómo lo detecté:** ejecuté cada hallazgo en lugar de leerlo (YAML con tipos inválidos, URL externas, `file:///etc/passwd`, una sonda con 100000 peticiones por segundo) y corrí pip-audit, que encontró las vulnerabilidades.
- **Qué hice:** corregí los 8 hallazgos reales, un commit por corrección, en la rama `semana-6-revision` integrada por pull request; descarté los falsos positivos señalando la línea que los desmiente. Detalle: [revision_seguridad.md](revision_seguridad.md); por ejemplo [`e6f8c02`](https://github.com/Andresprov/CaosLab/commit/e6f8c02) (starlette) y [`4227d7a`](https://github.com/Andresprov/CaosLab/commit/4227d7a) (solo contenedores `caoslab-*`).

### Caso 4: casos de prueba de un contrato que no era el mío

- **Fase:** requisitos y pruebas
- **Qué propuso la IA:** siete casos de prueba de límite para `evaluar_estado_estable()`.
- **Qué estaba mal:** cuatro (marcas de tiempo desordenadas, ventanas solapadas, muestras duplicadas y `None` en la lista) no estaban en el criterio de aceptación de la HU-01; probarlos me obligaba a implementar comportamiento que nadie pidió.
- **Cómo lo detecté:** comparé cada caso con la tabla de casos límite del contrato.
- **Qué hice:** conservé tres casos, reescribí el del pico aislado con números que muestran la diferencia entre las dos formas de calcular el percentil (el que luego atrapó el Caso 1) y descarté los otros. Commit: [`d2bd7ef`](https://github.com/Andresprov/CaosLab/commit/d2bd7ef).

### Caso 5: pruebas generadas sin el contrato, con el esperado al revés

- **Fase:** pruebas
- **Qué propuso la IA:** con un prompt sin el contrato («escribe las pruebas con pytest para `evaluar_estado_estable()` y `cargar_experimento()`»), 11 pruebas.
- **Qué estaba mal:** 4 eran débiles (`is not None`, `isinstance(..., float)`, un `pytest.raises(Exception)`) y no fallaban con ninguna mutación. 3 tenían el esperado al revés de la regla: la lista vacía lanzando error en vez de devolver `MUESTRAS_INSUFICIENTES`, el borde inclusivo abortando y el p95 interpolado como numpy, el mismo error del Caso 1.
- **Cómo lo detecté:** comparé el esperado de cada prueba con el contrato y apliqué ocho mutaciones al código para ver qué pruebas fallaban. Las débiles no fallaban con ninguna.
- **Qué hice:** descarté las débiles y corregí las 3 contra el contrato. Con el contrato en el prompt, la segunda generación salió casi bien. Dos pruebas del borrador sí encontraron defectos reales en `cargar_experimento()` (un número escrito como texto se escapaba como `TypeError` y una hipótesis en blanco pasaba): corregí el código, no las pruebas. Detalle: [registro_pruebas.md](registro_pruebas.md), [bitácora, entrada 20](bitacora_ia.md); commits [`38cc454`](https://github.com/Andresprov/CaosLab/commit/38cc454) y [`5fb5c70`](https://github.com/Andresprov/CaosLab/commit/5fb5c70).

## 5. Estado final del sistema

- **Arquitectura:** un motor (`motor.py`) coordina tres piezas intercambiables: una sonda HTTP (`sonda.py`) que mide a ritmo fijo con un hilo y un pool, un inyector (`inyectores.py`) definido como `Protocol` con `inyectar()` y `revertir()`, y la evaluación pura del estado estable (`estado_estable.py`). La reversión va en un `finally` y las señales de parada piden una salida ordenada. El CLI (`cli.py`) carga `experimento.yaml`, corre el motor y escribe el informe. Detalle en [README.md](README.md) y [DOCUMENTACION.txt](DOCUMENTACION.txt).
- **Funcionalidades terminadas:**
  - HU-01, detener el experimento cuando se agota el presupuesto de error: terminada ([contrato](docs/contrato_hu01.md)).
  - Comando `caoslab run` con informe en consola y en archivo: terminado.
  - Inyección de fallo por pausa de contenedor con reversión garantizada: terminada.
  - HU-04, aprobación humana antes de inyectar: pendiente (ver abajo).
- **Pruebas:** 234 pruebas unitarias y 3 de integración con Docker, todas en verde. Las 12 de la HU-01 no cambiaron desde que se escribieron. ruff (reglas E, F, B y S) sin avisos y pip-audit sin vulnerabilidades. La cobertura no se midió con una herramienta de cobertura de líneas; en su lugar, la lógica del negocio (`estado_estable.py`, `configuracion.py`, `motor.py`, `inyectores.py` e `informe.py`) se probó con particiones, valores límite y tablas de decisión, y las 8 mutaciones de [herramientas/mutar.py](herramientas/mutar.py) hacen fallar al menos una prueba cada una ([registro_pruebas.md](registro_pruebas.md)). El pipeline de [GitHub Actions](.github/workflows/ci.yml) corre ruff, las pruebas unitarias, pip-audit y las pruebas de integración con la app demo levantada en Docker. Ejecuciones sobre `main`: [Actions, ci.yml](https://github.com/Andresprov/CaosLab/actions/workflows/ci.yml?query=branch%3Amain).
- **Pendientes:**
  - HU-04, aprobación humana antes de inyectar el fallo: quedó para la entrega 2 porque es una historia completa, no una corrección.
  - Permiso por etiqueta `caoslab.permitido=true` en lugar del prefijo `caoslab-`, que es débil (RNF-04): requiere cambiar el doble de prueba `ContenedorFalso`.
  - Otros fallos (latencia, CPU, kill): el `Protocol` del inyector ya los permite sin tocar el motor.

## 6. Reflexión ética y legal

| Principio | Decisión en mi proyecto | Evidencia |
|---|---|---|
| Datos personales (Ley 1581 de 2012) | CaosLab no recoge datos personales. La app demo solo guarda pedidos sintéticos (producto y cantidad) y la sonda registra éxito y latencia, sin contenido de las respuestas. | [app_demo/main.py](app_demo/main.py), [caoslab/modelos.py](caoslab/modelos.py) |
| Sesgo | CaosLab no toma decisiones sobre personas, así que el sesgo que importó fue el de la IA y el mío. La IA tendía a soluciones genéricas (numpy, mensajes de error en inglés, casos de prueba de otro contrato) y yo tendía a confiar en las pruebas en verde. Lo mitigué escribiendo el contrato antes del código y probando los casos límite donde las fórmulas se separan. | [bitácora, entradas 1 a 3](bitacora_ia.md) |
| Transparencia | Cada sugerencia de la IA está en la bitácora con su decisión y verificación, y los commits hechos con IA llevan `Co-Authored-By: Claude`. Cerca del 85 % de las líneas actuales están en commits con participación de la IA. | [bitacora_ia.md](bitacora_ia.md), `git log` |
| Responsabilidad | El sistema inyecta fallos, así que se limitó a la copia local (URL de localhost y contenedores `caoslab-*`), con duración y ritmo máximos, y el fallo siempre se revierte. Revisé cada cambio del agente en un pull request antes de integrarlo. | [revision_seguridad.md](revision_seguridad.md), [bitácora, entrada 9](bitacora_ia.md) |
| Propiedad intelectual y política de uso | El proyecto tiene licencia MIT. Las dependencias tienen licencias permisivas: PyYAML, pytest, ruff y FastAPI son MIT; el SDK de Docker y pip-audit, Apache 2.0; uvicorn, BSD; psycopg, LGPL 3.0, y solo corre dentro de la imagen de la app demo. El uso de IA está declarado en la bitácora, en el README y en los commits. | [LICENSE](LICENSE) |

El dilema más importante apareció cuando falló la prueba del pico aislado. La
salida fácil era cambiar el valor esperado de 100.0 a 5000.0, lo que devolvía
el código: las 12 pruebas habrían quedado en verde y nadie lo habría notado.
Pero eso habría escondido un defecto real, y el agente habría abortado
experimentos sanos cada vez que una petición de veinte se demorara. Decidí que
la prueba tenía razón porque salía de un contrato escrito antes del código, y
corregí el código ([bitácora, entrada 6](bitacora_ia.md)). Hay un segundo dilema
de fondo: una herramienta que inyecta fallos puede dañar sistemas ajenos si se
usa mal. Por eso la limité a URL locales y a contenedores `caoslab-*`, con
duración y ritmo máximos, y la reversión del fallo no depende de que el
experimento termine bien.

## 7. Aprendizajes

**Qué sé hacer ahora.** Escribir el contrato de una función antes del código
y usarlo para decidir quién tiene razón cuando una prueba falla. Diseñar pruebas
de límite que separan dos implementaciones parecidas, como el caso de n = 20 en
el p95. Garantizar que un efecto se revierta con `try/finally` y captura de
señales. Y revisar la seguridad ejecutando cada hallazgo en vez de leerlo,
apoyado en herramientas como ruff y pip-audit.

**En qué confié de más en la IA.** En la velocidad. La estructura de la primera
versión era razonable y llegaba en un minuto, pero el único cálculo con algo de
sutileza, el percentil, estaba mal y once pruebas en verde lo tapaban. En la
revisión de seguridad pasó algo parecido: la IA dio cinco falsos positivos y no
vio las 14 vulnerabilidades de starlette, que solo aparecieron con pip-audit.
También dejé que el agente escribiera módulos completos; cerca del 85 % de las
líneas actuales están en commits con participación de la IA, y eso me obliga a
conocer ese código tan bien como si lo hubiera escrito solo.

**Qué haría distinto.** Pegar el contrato completo en el prompt desde el primer
mensaje y no solo la firma, porque la mitad de lo que corregí eran cosas que el
contrato ya resolvía. Pedirle al asistente que explique un cálculo antes de
aceptarlo, no después de que falle una prueba. Escribir yo más del núcleo,
empezando por el motor y la sonda. Y montar desde el inicio un pipeline que
corra pytest, ruff y pip-audit en cada pull request.

## 8. Anexos

- Bitácora de uso de IA: [bitacora_ia.md](bitacora_ia.md)
- Contrato de la HU-01: [docs/contrato_hu01.md](docs/contrato_hu01.md)
- Revisión de código y seguridad: [revision_seguridad.md](revision_seguridad.md)
- Diseño y revisión de las pruebas (semana 7): [registro_pruebas.md](registro_pruebas.md)
- Pipeline de integración continua: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Documentación de los módulos: [DOCUMENTACION.txt](DOCUMENTACION.txt)
