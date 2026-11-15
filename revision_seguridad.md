# Informe de revisión de código y seguridad

Proyecto: CaosLab, agente de pruebas de caos controlado sobre Docker
Estudiante: Andrés David Trujillo
Fecha: 2026-11-14
Commit revisado: `caef884` (entrega 1, semana 5). Correcciones en la rama `semana-6-revision`.

## 1. Herramientas y criterios

- **Linter:** ruff 0.17.5 con las reglas E, F, B y S. La configuración está en `pyproject.toml`. La primera pasada dio 197 avisos: 149 S101, 46 E501 y 2 B904. Hoy quedan 0.
- **Auditoría de dependencias:** pip-audit 2.10.1. `requirements.txt` no tiene vulnerabilidades conocidas. `app_demo/requirements.txt` tenía 14 en starlette 0.41.3 (H-05) y hoy no tiene ninguna.
- **Lista de revisión:** la de la semana 6, con tres bloques: corrección y pruebas, diseño y legibilidad, y seguridad.
- **Revisión con IA:** Claude (Anthropic) con el prompt de revisión de la semana (sección 3).
- **Pruebas:** `pytest -m "not integracion"` da 75 pruebas en verde (eran 64), más 6 de `test_app_demo.py` cuando FastAPI está instalado. Ninguna prueba existente cambió de aserción.

### Puntos de seguridad revisados

| Punto | ¿Aplica? | Resultado |
|---|---|---|
| Inyección (consultas con parámetros) | Sí | Sin hallazgos. Las consultas de `app_demo/main.py` usan `%s` con parámetros (línea 65) y ninguna arma texto con datos del usuario. El YAML se lee con `yaml.safe_load`, que no ejecuta código, y no hay llamadas a shell ni a `subprocess`. |
| Secretos (código, historial, .gitignore, .env.example) | Sí | Busqué `password`, `secret`, `token`, `key` y `PRIVATE KEY` en `git log -p --all` y no hay claves en el historial. Encontré dos problemas: la base de datos sin contraseña (H-03) y un `.gitignore` que impedía subir `.env.example` (H-04). Ambos están corregidos. |
| Contraseñas (scrypt, bcrypt o argon2 con sal) | No | CaosLab no tiene usuarios ni guarda contraseñas. La única contraseña del proyecto es la de PostgreSQL de la app demo, que ahora vive en `.env` (H-03). |
| Control de acceso (rol verificado y prueba de abuso) | Sí | CaosLab no tiene roles de usuario, pero sí dos operaciones restringidas: pausar un contenedor y mandar tráfico a una URL. Antes cualquier contenedor y cualquier URL eran válidos (H-01 y H-02). Ahora solo se permiten contenedores `caoslab-*` y URL locales, con 7 pruebas de abuso. La aprobación humana antes de inyectar (HU-04) sigue pendiente. |
| Dependencias (existen, necesarias, versión fijada, pip-audit) | Sí | Todas existen en PyPI y la tabla del README explica para qué sirve cada una. No tenían versión fijada (H-06) y starlette era vulnerable (H-05). Ambos están corregidos y pip-audit queda limpio en los dos archivos. |

## 2. Tabla de hallazgos

Las líneas son las del commit revisado, `caef884`.

| Id | Archivo y línea | Problema | Categoría (OWASP o tipo) | Severidad | Corrección | Commit |
|---|---|---|---|---|---|---|
| H-01 | caoslab/configuracion.py:46 | La URL de la sonda podía apuntar a cualquier servidor (5 peticiones por segundo contra un sitio ajeno) o usar `file://` | A01 Control de acceso roto / A10 SSRF | Alta | Solo `http(s)` hacia `localhost`, `127.0.0.1` o `::1`. 3 pruebas, 2 de abuso | `0e3b5e2` |
| H-02 | caoslab/configuracion.py:47 e inyectores.py:52 | Se podía pausar cualquier contenedor de la máquina, por ejemplo una base de datos real | A01 Control de acceso roto | Alta | Solo contenedores `caoslab-*`, validado en la configuración y otra vez en el inyector. 4 pruebas de abuso | `4227d7a` |
| H-03 | docker-compose.yml:8 | PostgreSQL con `POSTGRES_HOST_AUTH_METHOD: trust`: se entraba sin contraseña | A07 Fallas de autenticación | Media (sin puertos fuera de compose) | Contraseña desde `.env`; compose no arranca si falta | `eb668a7` |
| H-04 | .gitignore:3 | El patrón `.env.*` también ignoraba `.env.example` | Secretos / configuración | Baja | Excepción `!.env.example` y archivo de ejemplo | `eb668a7` |
| H-05 | app_demo/requirements.txt:1 | fastapi 0.115.6 traía starlette 0.41.3 sin fijar, con 14 vulnerabilidades conocidas (CVE-2025-62727, CVE-2026-48710, CVE-2026-54282, entre otras) | A06 Componentes vulnerables | Alta | fastapi 0.163.0 con starlette 1.10.0 fijada; pip-audit limpio | `e6f8c02` |
| H-06 | requirements.txt:1-3 | Dependencias con rango (`>=`) y no versión fijada | A06 Componentes vulnerables | Media | Versiones exactas, más ruff y pip-audit | `563e5a6` |
| H-07 | caoslab/configuracion.py:61-63 | Un número escrito como texto en el YAML lanzaba `TypeError`, el CLI no lo atrapaba y mostraba un traceback en vez de salir con código 2 | Posible error / validación de entrada | Media | Validación de tipo con `ErrorConfiguracion`. 2 pruebas | `89430fc` |
| H-08 | caoslab/configuracion.py:52 y sonda.py:20 | Sin tope de carga: con 100000 peticiones por segundo la sonda crea un pool de 200002 hilos | A04 Diseño inseguro (denegación de servicio) | Media | Máximo 50 peticiones por segundo y 120 s de duración (RNF-01). 2 pruebas | `89430fc` |
| H-09 | app_demo/main.py:11-13 | `POST /pedidos` aceptaba cantidades negativas o de un millón y nombres de cualquier tamaño | A04 Diseño inseguro / validación | Media | `Field` con límites; 422 si no se cumplen. 6 pruebas | `e471ba5` |
| H-10 | app_demo/main.py:56 y 69 | `raise` dentro de `except` sin `from` (B904): se pierde la causa del 503 | Posible error | Baja | `raise ... from error` | `34f0681` |
| H-11 | caoslab/informe.py:22 y 95; tests/test_informe.py:22 | Líneas de más de 120 caracteres (E501) | Estilo | Baja | Se partieron las líneas; la prueba conserva la misma llamada y aserción | `74a95fe` |
| H-12 | caoslab/configuracion.py:30-65 y cli.py:42 | Función de 50 líneas y valores mágicos (10, 5, 5, 2, 1 y los códigos 0, 1, 2) | Mantenibilidad | Baja | `_construir` y `_validar`, más constantes con nombre | `061e8ab` |

**Severidad:** alta (permite acceder o cambiar datos sin permiso, o expone secretos), media (error probable o riesgo con condiciones), baja (estilo o mantenibilidad).

### Avisos del linter no corregidos

| Regla | Archivo y línea | Por qué se mantiene |
|---|---|---|
| S101 | tests/** (149 avisos) | `assert` es la forma normal de comprobar en pytest. Se ignora solo en `tests/` con `per-file-ignores`, así que en el código de producción sigue activa. |
| E501 a 88 | todo el proyecto | El límite se subió a 120 en `pyproject.toml` porque el código ya estaba escrito con ese ancho. Las 5 líneas que pasaban de 120 se corrigieron (H-11). |

## 3. Revisión con IA

**Prompt usado** (entrada 7 de `bitacora_ia.md`):

> Rol: eres un revisor de código senior especializado en seguridad de aplicaciones Python.
> Contexto: CaosLab es una herramienta de línea de comandos que lee experimento.yaml, mide una URL con una sonda HTTP, pausa un contenedor con el SDK de Docker y escribe un informe. Incluye una app demo en FastAPI con PostgreSQL. Te pego todos los archivos de caoslab/, app_demo/, docker-compose.yml, requirements.txt y .gitignore.
> Tarea: revisa el código con estos criterios, en orden: 1) inyección, 2) secretos y configuración, 3) contraseñas, 4) control de acceso (qué puede hacer quien escribe el YAML), 5) dependencias, 6) errores probables y validación de entrada, 7) legibilidad.
> Formato: una tabla Archivo:línea | Problema | Categoría OWASP | Severidad (Alta/Media/Baja) | Corrección sugerida. Separa en dos tablas los problemas que puedes asegurar leyendo el código y las sospechas que habría que comprobar.
> Restricciones: no reescribas archivos completos; si un criterio no tiene hallazgos, escribe «Sin hallazgos»; no inventes números de línea.

| Hallazgo de la IA | ¿Real o falso positivo? | Cómo lo verifiqué |
|---|---|---|
| Seguro: número como texto en el YAML da `TypeError` (configuracion.py:61) | Real (H-07) | Cargué `duracion_s: "treinta"` con un script: salió `TypeError`, no `ErrorConfiguracion`. |
| Seguro: la URL no tiene restricción (configuracion.py:46) | Real (H-01) | `https://example.com/` y `file:///etc/passwd` cargaron sin error. Con `file://`, la sonda lanza `TypeError` dentro del hilo y la muestra se pierde. |
| Seguro: se puede pausar cualquier contenedor (configuracion.py:47) | Real (H-02) | `contenedor: postgres-produccion` cargó sin error y el inyector lo habría buscado. |
| Seguro: sin tope de peticiones por segundo (sonda.py:20) | Real (H-08) | Creé `SondaHTTP(url, 100000, 2)`: el pool quedó configurado con 200002 hilos. |
| Seguro: PostgreSQL con `trust` (docker-compose.yml:8) | Real (H-03) | Lo leí en el archivo y comprobé con `docker compose config` cómo queda después de corregirlo. |
| Seguro: dependencias con `>=` (requirements.txt) | Real (H-06) | Lo leí en el archivo: con `>=` cada instalación puede traer una versión distinta de la que se probó. |
| Seguro: `PedidoNuevo` sin límites (app_demo/main.py:11) | Real (H-09) | El modelo no tenía `Field`. Después de corregirlo, el cliente de pruebas responde 422 a cantidad -5, a un nombre vacío y a uno de 5000 caracteres. |
| Sospecha: carrera entre `recoger()` y `_medir()` sobre `_muestras` | Falso positivo | Los dos accesos están dentro de `with self._candado` (sonda.py:27 y 53). |
| Sospecha: inyección SQL en el `INSERT` | Falso positivo | Usa `%s` con una tupla de parámetros y psycopg los manda aparte de la consulta. |
| Sospecha: `yaml.load` puede ejecutar código | Falso positivo | El código usa `yaml.safe_load` (configuracion.py:35). |
| Sospecha: `fallo_inyectado = True` antes de inyectar hace que el informe diga «revertido» aunque la inyección falle | Falso positivo | Si `inyectar()` falla, la excepción sale del motor y el CLI responde 2 sin escribir informe; lo cubre `test_intenta_revertir_aunque_falle_la_inyeccion`. |
| Sospecha: `despausar_si_quedo_pausado()` despausa un contenedor que alguien pausó a propósito | Real, baja | Es cierto: no sabe quién lo pausó. Ahora solo toca contenedores `caoslab-*`, pero sigue en pendientes. |
| Sospecha: `os.environ["URL_BD"]` lanza `KeyError` | Falso positivo | Es intencional: la app demo no debe arrancar sin la URL de la base. |

Resultado: 8 reales y 5 falsos positivos.

**Lo que la IA no encontró:**

- **Las 14 vulnerabilidades de starlette (H-05), la más grave de la revisión.** La IA vio `fastapi==0.115.6` fijado y lo dio por bueno, pero starlette llegaba sin fijar y vulnerable. Lo encontró `pip-audit`, porque leyendo el código no se pueden conocer los CVE publicados.
- **El `.gitignore` que ignoraba `.env.example` (H-04).** Lo vi al crear el archivo, porque `git status` no lo mostraba; lo confirmé con `git check-ignore -v`.
- **Un YAML con la sintaxis rota lanza `yaml.YAMLError` sin atrapar,** con el mismo efecto de traceback que H-07. Lo encontré escribiendo el docstring de `cargar_experimento`. Queda pendiente.
- **ruff tampoco detectó el `file://`.** La regla S310 solo revisa llamadas directas a `urlopen` y la sonda usa un `opener`.

## 4. Pendientes

| Pendiente | Por qué no se corrigió todavía | Plan |
|---|---|---|
| Un YAML con sintaxis inválida lanza `yaml.YAMLError` y el CLI muestra un traceback | Lo encontré al final de la revisión y cambia el contrato de `cargar_experimento` | Convertirlo en `ErrorConfiguracion` con una prueba nueva, en la semana 7 |
| El permiso por prefijo de nombre (`caoslab-`) es débil: quien use Docker puede nombrar así cualquier contenedor | La etiqueta exige cambiar el doble de prueba `ContenedorFalso` y quise no tocar pruebas existentes en esta entrega | Exigir la etiqueta `caoslab.permitido=true` (RNF-04) en la entrega 2 |
| No hay aprobación humana antes de inyectar el fallo (HU-04) | Es una historia completa, no una corrección | Backlog de la entrega 2 |
| `despausar_si_quedo_pausado()` no sabe si el contenedor lo pausó CaosLab | Hace falta guardar estado entre corridas | Marcar el contenedor con una etiqueta al pausarlo |
| Si un hilo de la sonda lanza algo distinto de `URLError` u `OSError`, la muestra se pierde en silencio | Hoy solo pasaba con `file://`, que ya está bloqueado | Contar esa petición como fallida y agregar una prueba |
| `docker compose up` y `caoslab run` con la contraseña nueva no se probaron con Docker real durante la revisión | El entorno de la revisión no tenía Docker; sí se comprobó `docker compose config` | Correr `pytest -m integracion` antes de integrar la rama |

**Claves expuestas:** ninguna. Busqué en todo el historial con `git log -p --all` y no encontré claves. La base de datos nunca tuvo contraseña (usaba `trust`), así que no hubo nada que cambiar.
