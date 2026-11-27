# Registro de pruebas: tabla de casos y pruebas de la IA

Proyecto: CaosLab — agente de pruebas de caos controlado sobre una aplicación en Docker
Estudiante: Andrés David Trujillo
Fecha: 2026-11-22

Suite de la semana 7: `tests/test_semana7_*.py` y los datos sintéticos de
`tests/conftest.py`. Se suman a las pruebas de las semanas 5 y 6, que siguen en
verde. Estado actual: **217 pruebas pasan** con `pytest -m "not integracion"`
(3 más necesitan Docker levantado).

Los esperados de todas las tablas salen de dos documentos escritos antes del
código: el contrato de la HU-01 en el `README.md` (criterio de aceptación, casos
límite, casos de error y la nota de diseño **ADR-002: el umbral es inclusivo**) y
la sección 9 de `DOCUMENTACION.txt` para el informe. Ninguno salió de ejecutar
el código.

---

## 1. Tabla de casos

### 1.1 Regla: `evaluar_estado_estable()` decide si el experimento sigue o se detiene

**Regla completa (el oráculo):** HU-01 del README. Como ingeniero de
confiabilidad, quiero que CaosLab evalúe el estado estable del sistema durante
un experimento de caos y lo detenga cuando la tasa de error o la latencia
superen el presupuesto acordado, para que un experimento no degrade el servicio
más allá de lo que el equipo aceptó de antemano. Si hay menos muestras que
`minimo_muestras`, el veredicto es `MUESTRAS_INSUFICIENTES` y **no** se aborta,
con las métricas en `0.0`. El p95 se calcula por rango más cercano,
`indice = ceil(0.95 * n) - 1` sobre las latencias ordenadas. El umbral es
inclusivo (ADR-002): estar exactamente en el límite todavía está dentro del
presupuesto. La tasa y la latencia se evalúan por separado y el veredicto lista
todos los motivos.

| Técnica | Partición o límite | Entrada | Esperado | Prueba que lo cubre |
|---|---|---|---|---|
| Partición válida | Sistema sano | 20 exitosas de 100 ms, presupuesto (0.10, 300 ms, mín. 5) | `CONTINUAR`, sin motivos | `test_tabla_de_decision_del_estado_estable[R2-C1si-C2no-C3no]` |
| Partición válida | Solo la tasa agotada | 17 exitosas y 3 fallidas de 100 ms, presupuesto (0.10, 300, 5) | `ABORTAR`, 1 motivo de tasa | `test_tabla_de_decision_del_estado_estable[R3-C1si-C2si-C3no]` |
| Partición válida | Solo la latencia agotada | 20 exitosas de 400 ms, presupuesto (0.10, 300, 5) | `ABORTAR`, 1 motivo de latencia | `test_tabla_de_decision_del_estado_estable[R4-C1si-C2no-C3si]` |
| Partición válida | Las dos agotadas | 15 exitosas y 5 fallidas de 400 ms | `ABORTAR`, 2 motivos | `test_tabla_de_decision_del_estado_estable[R5-C1si-C2si-C3si]` |
| Partición válida | Sin evidencia | 2 fallidas de 9000 ms, mín. 5 | `MUESTRAS_INSUFICIENTES`, tasa 0.0, p95 0.0 | `test_sin_evidencia_no_reporta_metricas_inventadas` |
| Límite | Tasa por debajo del umbral | 1 fallida de 20, máx. 0.10 | tasa 0.05, `CONTINUAR` | `test_limites_de_la_tasa_de_error[19-1-0.1-0.05-CONTINUAR]` |
| Límite | Tasa **exactamente** en el umbral | 2 fallidas de 20, máx. 0.10 | tasa 0.10, `CONTINUAR` (inclusivo) | `test_limites_de_la_tasa_de_error[18-2-0.1-0.1-CONTINUAR]` |
| Límite | Primer valor que supera el umbral | 3 fallidas de 20, máx. 0.10 | tasa 0.15, `ABORTAR` | `test_limites_de_la_tasa_de_error[17-3-0.1-0.15-ABORTAR]` |
| Límite | `max_tasa_error = 0.0` sin fallos | 10 exitosas, máx. 0.0 | tasa 0.0, `CONTINUAR` | `test_limites_de_la_tasa_de_error[10-0-0.0-0.0-CONTINUAR]` |
| Límite | `max_tasa_error = 0.0` con un fallo | 1 fallida de 10, máx. 0.0 | tasa 0.10, `ABORTAR` | `test_limites_de_la_tasa_de_error[9-1-0.0-0.1-ABORTAR]` |
| Límite | `max_tasa_error = 1.0` con todo fallido | 20 fallidas, máx. 1.0 | tasa 1.0, `CONTINUAR` | `test_limites_de_la_tasa_de_error[0-20-1.0-1.0-CONTINUAR]` |
| Límite | p95 por debajo del umbral | 10 muestras de 299.9 ms, máx. 300 | `CONTINUAR` | `test_limites_de_la_latencia_p95[299.9-300.0-CONTINUAR]` |
| Límite | p95 **exactamente** en el umbral | 10 muestras de 300.0 ms, máx. 300 | `CONTINUAR` (inclusivo) | `test_limites_de_la_latencia_p95[300.0-300.0-CONTINUAR]` |
| Límite | Primer valor que lo supera | 10 muestras de 300.1 ms, máx. 300 | `ABORTAR` | `test_limites_de_la_latencia_p95[300.1-300.0-ABORTAR]` |
| Límite | Latencia 0 ms (borde inferior válido) | 10 muestras de 0.0 ms | p95 0.0, `CONTINUAR` | `test_limites_de_la_latencia_p95[0.0-300.0-CONTINUAR]` |
| Límite | Lista vacía con el mínimo más bajo | 0 muestras, mín. 1 | `MUESTRAS_INSUFICIENTES` | `test_limites_del_minimo_de_muestras[0-1-MUESTRAS_INSUFICIENTES]` |
| Límite | Una muestra menos que el mínimo | 4 muestras, mín. 5 | `MUESTRAS_INSUFICIENTES` | `test_limites_del_minimo_de_muestras[4-5-MUESTRAS_INSUFICIENTES]` |
| Límite | Exactamente el mínimo | 5 muestras, mín. 5 | `CONTINUAR` | `test_limites_del_minimo_de_muestras[5-5-CONTINUAR]` |
| Límite | Una muestra con mínimo 1 | 1 muestra, mín. 1 | `CONTINUAR`, p95 = su latencia | `test_limites_del_minimo_de_muestras[1-1-CONTINUAR]` |
| Límite | p95 con n = 1, 2, 10, 19 | latencias n…1 ms | `ceil(0.95n) - 1` → n.0 ms | `test_el_p95_es_una_latencia_realmente_observada[1-1.0]` … `[19-19.0]` |
| Límite | p95 con n = 20 (0.95·n entero) | latencias 20…1 ms | 19.0 ms, no 20.0 | `test_el_p95_es_una_latencia_realmente_observada[20-19.0]` |
| Límite | p95 con n = 21 y n = 40 | latencias n…1 ms | 20.0 ms y 38.0 ms | `test_el_p95_es_una_latencia_realmente_observada[21-20.0]`, `[40-38.0]` |
| Partición inválida | `max_tasa_error` justo por debajo de 0.0 | −0.01 | `ValueError` que nombra `max_tasa_error` | `test_presupuesto_invalido_lanza_value_error[presupuesto0-max_tasa_error]` |
| Partición inválida | `max_tasa_error` justo por encima de 1.0 | 1.01 y 1.5 | `ValueError` | `test_presupuesto_invalido_lanza_value_error[presupuesto1…2-max_tasa_error]` |
| Partición inválida | `max_latencia_p95_ms` en el borde 0 y negativa | 0.0 y −5.0 | `ValueError` | `test_presupuesto_invalido_lanza_value_error[presupuesto3…4-max_latencia_p95_ms]` |
| Partición inválida | `minimo_muestras` menor que 1 | 0 y −3 | `ValueError` | `test_presupuesto_invalido_lanza_value_error[presupuesto5…6-minimo_muestras]` |
| Partición inválida | Latencia negativa | muestra 3 con −0.1 y con −1000.0 | `ValueError` que nombra la muestra 3 | `test_latencia_negativa_lanza_value_error_nombrando_la_muestra[-0.1-3]`, `[-1000.0-3]` |
| Límite válido | Bordes válidos del presupuesto a la vez | (0.0, 0.1 ms, 1) y (1.0, 300, 1) | no lanza | `test_los_bordes_validos_del_presupuesto_no_lanzan[presupuesto0…1]` |
| Partición válida | Volumen con pico aislado | 301 muestras sintéticas: 15 fallidas, pico de 9000 ms | tasa 15/301, p95 80 ms, `CONTINUAR` | `test_volumen_de_trescientas_muestras_con_un_pico_aislado` |
| Partición válida | Función pura | lista desordenada de 3 muestras | la lista de entrada queda igual | `test_la_funcion_no_muta_las_muestras_que_recibe` |

#### Tabla de decisión (la función combina tres condiciones)

- **C1:** hay al menos `minimo_muestras` muestras
- **C2:** tasa de error > `max_tasa_error`
- **C3:** latencia p95 > `max_latencia_p95_ms`

| Regla | C1 | C2 | C3 | Resultado | Prueba |
|---|---|---|---|---|---|
| R1 | no | — | — | `MUESTRAS_INSUFICIENTES`, 0 motivos, métricas en 0.0 | `[R1-C1no-C2y C3 indiferentes]` |
| R2 | sí | no | no | `CONTINUAR`, 0 motivos | `[R2-C1si-C2no-C3no]` |
| R3 | sí | sí | no | `ABORTAR`, 1 motivo (tasa) | `[R3-C1si-C2si-C3no]` |
| R4 | sí | no | sí | `ABORTAR`, 1 motivo (latencia) | `[R4-C1si-C2no-C3si]` |
| R5 | sí | sí | sí | `ABORTAR`, 2 motivos en orden: tasa y después latencia | `[R5-C1si-C2si-C3si]` |

Simplificación: con C1 en «no» las otras dos condiciones no importan, porque la
regla dice que sin evidencia no se calcula ninguna métrica. Eso reduce de ocho
combinaciones a cinco reglas. El caso de R1 se arma a propósito con datos que
violarían C2 y C3 (2 muestras fallidas de 9000 ms), para que la prueba falle si
alguien algún día decide abortar sin evidencia suficiente.

**Ambigüedades encontradas:**

1. **Qué error gana cuando el presupuesto y las muestras están mal a la vez.** El
   contrato lista los cuatro casos de error por separado y no dice en qué orden
   se validan. La implementación valida primero el presupuesto. Lo dejé así
   (el presupuesto es el acuerdo previo del equipo, revisarlo primero es lo
   razonable) pero **no escribí una prueba de ese orden**, para no congelar en
   la suite un detalle que nadie decidió. Queda anotado para preguntarle al
   docente.
2. **El rango del presupuesto no se valida al leer el YAML.** `cargar_experimento()`
   acepta `max_tasa_error: 5.0` y el error aparece después, cuando corre
   `evaluar_estado_estable()`. Decidí mantener esa separación: el cargador valida
   la forma y el tipo del archivo, el rango lo valida la función que lo usa, y el
   CLI traduce las dos cosas a código de salida 2, así que el usuario ve un
   mensaje claro igual. Está anotado en la sección 1.2.

---

### 1.2 Regla: `cargar_experimento()` lee y valida `experimento.yaml`

**Regla completa (el oráculo):** README, sección «experimento.yaml». Son
obligatorios `hipotesis`, `objetivo.url`, `objetivo.contenedor`, `fallo.tipo`,
`duracion_s`, `presupuesto.max_tasa_error` y `presupuesto.max_latencia_p95_ms`.
Son opcionales, con estos valores por omisión: `nombre` = «experimento»,
`linea_base_s` = 10, `ventana_s` = 5, `peticiones_por_segundo` = 5,
`timeout_s` = 2 y `minimo_muestras` = 1. El único tipo de fallo de esta entrega
es `pausar`. Los campos de tiempo y de ritmo deben ser mayores que 0. Según la
tabla de códigos de salida, un archivo mal escrito termina en código 2, y el CLI
solo traduce a 2 lo que llegue como `ValueError`, así que todo error de
configuración tiene que ser `ErrorConfiguracion` (que hereda de `ValueError`).

| Técnica | Partición o límite | Entrada | Esperado | Prueba que lo cubre |
|---|---|---|---|---|
| Partición válida | Archivo completo | los 11 campos escritos | cada campo se lee tal cual | `test_lee_todos_los_campos_de_un_archivo_completo` |
| Partición válida | Archivo mínimo | solo los obligatorios | los cuatro opcionales toman 10, 5, 5 y 2 | `test_los_campos_opcionales_usan_su_valor_por_omision[…]` |
| Partición válida | Mínimo de muestras por omisión | sin `minimo_muestras` | 1 | `test_el_minimo_de_muestras_por_omision_es_uno` |
| Partición válida | Texto con tildes, ñ y apóstrofo | los 4 experimentos sintéticos del conftest | el texto se lee sin cambios | `test_lee_tildes_ene_y_apostrofo_sin_romper_el_texto` |
| Límite | Campo positivo en 0 (fuera) | `duracion_s: 0`, y los otros 4 campos | `ErrorConfiguracion` «debe ser mayor que 0» | `test_limites_de_los_campos_que_deben_ser_positivos[0-False-*]` |
| Límite | Primer valor válido | `duracion_s: 0.1`, y los otros 4 | se acepta y vale 0.1 | `test_limites_de_los_campos_que_deben_ser_positivos[0.1-True-*]` |
| Partición inválida | Campo positivo negativo | −1 en los 5 campos | `ErrorConfiguracion` | `test_limites_de_los_campos_que_deben_ser_positivos[-1-False-*]` |
| Partición inválida | Archivo que no existe | ruta inexistente | `ErrorConfiguracion` «no existe» | `test_un_archivo_que_no_existe_lanza_error_configuracion` |
| Partición inválida | Archivo vacío | `""` | `ErrorConfiguracion` «falta el campo obligatorio» | `test_cada_campo_obligatorio_que_falta_se_nombra_en_el_error[-…]` |
| Partición inválida | Cada obligatorio ausente, uno a la vez | 7 archivos, cada uno sin un campo | el mensaje nombra ese campo | `test_cada_campo_obligatorio_que_falta_se_nombra_en_el_error[texto2…texto7]` |
| Partición inválida | Tipo de fallo inexistente | `latencia`, `cpu`, `matar`, `PAUSAR`, `pausa` | `ErrorConfiguracion` «no existe» | `test_un_tipo_de_fallo_que_no_existe_lanza_error_configuracion[…]` |
| Partición inválida | Texto obligatorio en blanco | `''` y `'   '` en hipótesis, url y contenedor | `ErrorConfiguracion` «está vacío» | `test_un_campo_de_texto_obligatorio_vacio_lanza_error_configuracion[…]` |
| Partición inválida | Campo numérico con texto | `treinta` y `'30 s'` en los 8 campos numéricos | `ErrorConfiguracion` «debe ser un número» | `test_un_campo_numerico_con_texto_lanza_error_configuracion[…]` |

**Ambigüedades encontradas:** las dos últimas filas no estaban resueltas en el
contrato y salieron de diseñar las particiones inválidas. Las dos eran defectos
reales y se corrigieron en el código, no en las pruebas (ver sección 2, D-01 y
D-02). El rango del presupuesto sigue validándose en `evaluar_estado_estable()`
y no al cargar, por la decisión de la ambigüedad 2 de la sección 1.1.

---

### 1.3 Regla: `ejecutar_experimento()` decide la conclusión del experimento

**Regla completa (el oráculo):** README, sección «Cómo decide el motor».
(1) Mide la línea base; si no da `CONTINUAR` no inyecta nada y la conclusión es
`LINEA_BASE_INESTABLE`. (2) Inyecta el fallo y evalúa cada ventana con las
muestras de esa ventana. (3) La primera ventana con `ABORTAR` detiene el
experimento: `ABORTADO`. (4) Una ventana con `MUESTRAS_INSUFICIENTES` no aborta;
si ninguna juntó evidencia el resultado es `SIN_EVIDENCIA` y no `SUPERADO`.
(5) Si todas las ventanas pasan: `SUPERADO`. Una señal de parada deja
`INTERRUMPIDO`. El número de ventanas es `ceil(duracion_s / ventana_s)`. Y de la
sección «Reversión garantizada»: si el fallo se inyectó, se revierte pase lo que
pase; si no se inyectó, no hay nada que revertir.

| Técnica | Partición o límite | Entrada | Esperado | Prueba que lo cubre |
|---|---|---|---|---|
| Partición válida | Todas las ventanas aguantan | línea base sana + 3 ventanas sanas | `SUPERADO`, 3 ventanas, se inyecta y se revierte | `test_tabla_de_decision_de_la_conclusion[R6-C1si-C2no-C3no-C4no]` |
| Partición válida | Línea base fuera del presupuesto | línea base 10 fallidas | `LINEA_BASE_INESTABLE`, 0 ventanas, el inyector no se toca | `[R1-C1no-por-presupuesto-agotado]` |
| Partición válida | Línea base sin muestras suficientes | línea base de 2 muestras, mín. 5 | `LINEA_BASE_INESTABLE`, 0 ventanas | `[R2-C1no-por-falta-de-muestras]` |
| Partición válida | Señal de parada durante el fallo | Ctrl+C en la segunda recolección | `INTERRUMPIDO`, se revierte, la sonda se detiene | `[R3-C1si-C2si]` |
| Partición válida | Una ventana agota el presupuesto | ventana 2 con 10 fallidas | `ABORTADO`, 2 ventanas | `[R4-C1si-C2no-C3si]` |
| Partición válida | Ninguna ventana junta evidencia | 3 ventanas vacías | `SIN_EVIDENCIA`, 3 ventanas | `[R5-C1si-C2no-C3no-C4si]` |
| Partición válida | Mezcla: una ventana sin evidencia | sanas, 2 muestras, sanas | `SUPERADO` con la ventana 2 en `MUESTRAS_INSUFICIENTES` | `test_una_ventana_sin_evidencia_entre_ventanas_sanas_no_impide_superar` |
| Partición válida | El aborto detiene la medición | ventana 1 con 10 fallidas | 1 ventana y 2 recolecciones en total | `test_aborta_en_la_primera_ventana_mala_y_deja_de_medir` |
| Límite | `ceil` con duración menor que la ventana | 1 s en ventanas de 5 s | 1 ventana | `test_limites_del_numero_de_ventanas[1-5-1]` |
| Límite | `ceil` exacto | 5/5 y 10/5 | 1 y 2 ventanas | `test_limites_del_numero_de_ventanas[5-5-1]`, `[10-5-2]` |
| Límite | Primer valor que agrega una ventana | 6/5 y 11/5 | 2 y 3 ventanas | `test_limites_del_numero_de_ventanas[6-5-2]`, `[11-5-3]` |
| Límite | El experimento del README | 30 s en ventanas de 5 s | 6 ventanas | `test_limites_del_numero_de_ventanas[30-5-6]` |
| Límite | Orden de las esperas | 10/5 y 5/5 | `[10, 5, 5]` y `[10, 5]` | `test_espera_la_linea_base_y_despues_cada_ventana[…]` |
| Partición inválida | Excepción a mitad del experimento | `RuntimeError`, `KeyboardInterrupt`, `MemoryError` | la excepción sube y el fallo queda revertido | `test_revierte_el_fallo_aunque_salte_cualquier_excepcion[…]` |
| Partición inválida | La inyección misma falla | el inyector lanza al inyectar | `RuntimeError` y se revierte igual | `test_revierte_aunque_la_inyeccion_misma_falle` |

#### Tabla de decisión (la segunda función que combina condiciones)

- **C1:** la línea base dio `CONTINUAR`
- **C2:** llegó una señal de parada
- **C3:** alguna ventana dio `ABORTAR`
- **C4:** todas las ventanas dieron `MUESTRAS_INSUFICIENTES`

| Regla | C1 | C2 | C3 | C4 | Conclusión | Eventos del inyector |
|---|---|---|---|---|---|---|
| R1 y R2 | no | — | — | — | `LINEA_BASE_INESTABLE` | ninguno: no se inyectó |
| R3 | sí | sí | — | — | `INTERRUMPIDO` | inyectar, revertir |
| R4 | sí | no | sí | — | `ABORTADO` | inyectar, revertir |
| R5 | sí | no | no | sí | `SIN_EVIDENCIA` | inyectar, revertir |
| R6 | sí | no | no | no | `SUPERADO` | inyectar, revertir |

Simplificación: con C1 en «no» nada más importa, porque el fallo no se llega a
inyectar; y con C2 en «sí» el motor sale del ciclo sin cerrar la ventana, así que
C3 y C4 no alcanzan a evaluarse. De dieciséis combinaciones quedan seis reglas.

---

### 1.4 Regla: `InyectorPausa` pausa y revierte sin tocar lo que no es suyo

**Regla completa (el oráculo):** README, secciones «Cómo decide el motor» y
«Reversión garantizada», más la tabla de códigos de salida: un contenedor
inexistente o en un estado que no se puede pausar termina en código 2, es decir
en `ErrorInyeccion`. Revertir solo despausa el contenedor que este experimento
pausó y solo si sigue pausado. Al empezar cada corrida, CaosLab revisa si el
contenedor quedó pausado de una corrida anterior matada a la fuerza y, si es
así, lo despausa.

| Técnica | Partición o límite | Entrada | Esperado | Prueba que lo cubre |
|---|---|---|---|---|
| Partición válida | Contenedor corriendo | `status = running` | se pausa una vez | `test_pausa_el_contenedor_cuando_esta_corriendo` |
| Partición inválida | Estados que no se pueden pausar | `paused`, `exited`, `created`, `restarting`, `dead` | `ErrorInyeccion` que nombra el estado, 0 pausas | `test_un_contenedor_que_no_esta_corriendo_lanza_error_inyeccion[…]` |
| Partición inválida | Contenedor inexistente | Docker lanza `NotFound` | `ErrorInyeccion` «no existe el contenedor caoslab-pedidos-db» | `test_un_contenedor_que_no_existe_lanza_error_inyeccion` |
| Límite | Revertir dos veces | revertir repetido tras una pausa | una sola despausa | `test_revertir_dos_veces_despausa_una_sola_vez` |
| Partición válida | Rescate de una corrida anterior | `paused` / `running` / `exited` | `True` y 1 despausa / `False` y 0 / `False` y 0 | `test_despausar_si_quedo_pausado[…]` |
| Partición válida | Descripción para la consola | contenedor `caoslab-pedidos-db` | «pausar el contenedor caoslab-pedidos-db» | `test_la_descripcion_nombra_el_contenedor_objetivo` |

#### Tabla de decisión de `revertir()`

- **C1:** este inyector fue el que pausó el contenedor
- **C2:** el contenedor sigue pausado ahora

| Regla | C1 | C2 | Resultado | Prueba |
|---|---|---|---|---|
| R1 | no | sí | no se despausa: no es nuestro | `test_tabla_de_decision_de_revertir[False-paused-0]` |
| R2 | no | no | no se despausa | `[False-running-0]` |
| R3 | sí | no | no se despausa: alguien más ya lo hizo | `[True-running-0]` |
| R4 | sí | sí | se despausa una vez | `[True-paused-1]` |

R1 es el caso que más importa: si `revertir()` despausara cualquier contenedor
pausado, un experimento podría levantar un contenedor que otra persona pausó a
mano. La mutación M6 de la sección 3 es justo ese error y esta fila lo atrapa.

---

### 1.5 Regla: `generar_informe()` deja por escrito qué pasó

**Regla completa (el oráculo):** `DOCUMENTACION.txt`, sección 9. El informe
lleva la hipótesis, la configuración, la línea base, una tabla con cada ventana
(muestras, tasa de error, p95 y estado), el veredicto con una frase que lo
explica, los motivos si hubo y si el fallo se revirtió. Los motivos salen de la
ventana que abortó o, si la línea base falló, de la línea base; si la línea base
falló por falta de muestras, el motivo dice cuántas juntó y cuántas hacían falta.
`escribir_informe()` guarda ese mismo texto.

| Técnica | Partición o límite | Entrada | Esperado | Prueba que lo cubre |
|---|---|---|---|---|
| Partición válida | Una fila por conclusión | `SUPERADO`, `ABORTADO`, `LINEA_BASE_INESTABLE`, `SIN_EVIDENCIA` | el veredicto en negrita, «Motivos:» solo cuando la regla los pide, y la frase de reversión correcta | `test_el_informe_nombra_el_veredicto_y_si_se_revirtio[…]` |
| Partición válida | Origen de los motivos: aborto | experimento abortado | los motivos de la última ventana | `test_los_motivos_de_un_aborto_salen_de_la_ventana_que_aborto` |
| Partición válida | Origen de los motivos: línea base | línea base fuera del presupuesto | los motivos de la línea base y «El fallo no se llegó a inyectar.» | `test_los_motivos_de_una_linea_base_inestable_salen_de_la_linea_base` |
| Partición válida | Línea base sin muestras | 3 muestras con mínimo 5 | «solo juntó 3 muestras» y «el mínimo es 5» | `test_si_la_linea_base_no_junto_muestras_el_motivo_dice_cuantas_faltaron` |
| Límite | Filas de la tabla de ventanas | 15/5, 10/5 y 5/5 | 3, 2 y 1 filas | `test_la_tabla_lleva_una_fila_por_ventana_medida[…]` |
| Partición válida | Texto con tildes, ñ y apóstrofo | los 4 experimentos sintéticos | el nombre, la hipótesis, el contenedor y la URL salen tal cual | `test_el_informe_conserva_tildes_ene_y_apostrofo` |
| Partición válida | Archivo en disco | informe de «Café D'Anita» | el archivo en UTF-8 es idéntico al texto de consola | `test_el_archivo_del_informe_se_guarda_en_utf8` |
| Límite | Formato del porcentaje | 0.0, 0.05, 0.125 y 1.0 | «0.00 %», «5.00 %», «12.50 %», «100.00 %» | `test_el_presupuesto_se_imprime_con_dos_decimales[…]` |

**Ambigüedades encontradas:** el contrato dice qué secciones lleva el informe
pero no fija las frases exactas, así que las pruebas comprueban lo que la regla
sí decide (que esté el veredicto, que los motivos vengan de la fuente correcta,
que la tabla tenga una fila por ventana, que el texto no se corrompa) y no las
palabras de cada frase, que son decisión de redacción y van a cambiar.

---

## 2. Pruebas de la IA descartadas o corregidas

**Prompt usado:** «Dale, escribí las pruebas con pytest para `evaluar_estado_estable()`
y `cargar_experimento()` de CaosLab» — a propósito **sin pasarle el contrato**, para
ver qué produce la IA cuando tiene que adivinar la regla. Ese primer borrador quedó
en 11 pruebas. Después repetí la generación pegándole el contrato del README y mi
tabla de casos ya revisada, exigiendo `@pytest.mark.parametrize` con un comentario
por fila, `pytest.approx` para decimales, `pytest.raises` con el tipo exacto y
esperados fijos. Las entradas 1, 2 y 3 de `bitacora_ia.md` tienen el detalle.

De las 11 pruebas del primer borrador: **4 conservadas con cambios de forma,
3 corregidas porque el esperado contradecía la regla, 4 descartadas por débiles.**

| Prueba generada | Decisión | Por qué | En su lugar |
|---|---|---|---|
| `test_tasa_justo_en_el_umbral_aborta`: 2 fallidas de 10 con máx. 0.20, espera `ABORTAR` | Corregida | El esperado contradice el ADR-002: el umbral es inclusivo, 0.20 todavía está dentro. La IA adivinó la semántica del borde en vez de leerla. | Fila `(18, 2, 0.10, 0.10, CONTINUAR)` de `test_limites_de_la_tasa_de_error`, con el borde de arriba y el de abajo al lado |
| `test_p95_de_veinte_muestras_es_el_maximo`: espera p95 = 5000 ms con 19 muestras de 100 ms y un pico | Corregida | Asume percentil interpolado al estilo de `numpy`. El contrato pide rango más cercano: `ceil(0.95·20) − 1 = 18`, o sea 100 ms. Es el mismo error que ya me había costado un defecto en la semana 5. | `test_el_p95_es_una_latencia_realmente_observada`, 7 filas con n = 1, 2, 10, 19, 20, 21 y 40, y el índice calculado en el comentario de cada fila |
| `test_lista_vacia_lanza_error`: espera `ValueError` con la lista vacía | Corregida | El contrato dice lo contrario: sin evidencia no se toma una decisión destructiva, la lista vacía devuelve `MUESTRAS_INSUFICIENTES` con las métricas en 0.0. Si la hubiera conservado, habría documentado un comportamiento peligroso como si fuera el correcto. | `test_limites_del_minimo_de_muestras[0-1-MUESTRAS_INSUFICIENTES]` y `test_sin_evidencia_no_reporta_metricas_inventadas` |
| `test_evaluar_devuelve_algo`: `assert resultado is not None` | Descartada | Pasa con cualquier implementación que devuelva un objeto, incluso una que siempre conteste `ABORTAR`. No falla con ninguna de las 8 mutaciones de la sección 3. | nada: lo que quería comprobar ya lo cubre la tabla de decisión |
| `test_veredicto_tiene_estado_valido`: `assert estado in (CONTINUAR, ABORTAR, MUESTRAS_INSUFICIENTES)` | Descartada | Comprueba el `Enum`, no la regla: los tres valores son los únicos que existen, así que la prueba no puede fallar nunca. | nada |
| `test_tasa_de_error_es_un_numero`: `assert isinstance(tasa_error, float)` | Descartada | Comprueba el tipo que ya garantiza la `dataclass`. Un cálculo de la tasa completamente equivocado seguiría pasando. | la tasa exacta con `pytest.approx` en las 6 filas de `test_limites_de_la_tasa_de_error` |
| `test_presupuesto_invalido_lanza_excepcion`: `pytest.raises(Exception)` | Descartada | `Exception` atrapa cualquier cosa, hasta un `AttributeError` por un error de tipeo en el nombre de un campo. La tarea pide el tipo exacto. | `test_presupuesto_invalido_lanza_value_error`, 7 filas con `ValueError` y `match` del campo que está mal |
| `test_archivo_inexistente_lanza_error`: `pytest.raises(Exception)` | Conservada con cambios | El caso sí es del contrato, pero el tipo era demasiado amplio. | `test_un_archivo_que_no_existe_lanza_error_configuracion`, con `ErrorConfiguracion` y `match="no existe"` |
| `test_duracion_cero_lanza_error_configuracion` | Conservada con cambios | El caso es correcto y el tipo también, pero probaba un solo campo y un solo lado del borde. | `test_limites_de_los_campos_que_deben_ser_positivos`, 15 filas: −1, 0 y 0.1 por cada uno de los 5 campos positivos |
| `test_duracion_texto_lanza_error_configuracion`: `duracion_s: treinta` | Conservada, **reveló el defecto D-01** | La prueba falló con `TypeError: '<=' not supported between instances of 'str' and 'int'`. No era un esperado mal puesto: el cargador comparaba el valor con 0 sin revisar que fuera un número, y el CLI solo traduce `ValueError` a código 2, así que el usuario veía un *traceback* en vez del mensaje de error. **Corregí el código**, no la prueba: agregué `_numero()` en `caoslab/configuracion.py` (al integrarse con la revisión de seguridad de la semana 6 quedó como `_validar_numero()`), que lanza `ErrorConfiguracion` nombrando el campo. | `test_un_campo_numerico_con_texto_lanza_error_configuracion`, 16 filas: dos textos por cada uno de los 8 campos numéricos, incluidos los tres del presupuesto |
| `test_hipotesis_vacia_lanza_error_configuracion`: `hipotesis: ''` | Conservada, **reveló el defecto D-02** | La prueba falló con «DID NOT RAISE». El contrato dice que la hipótesis es obligatoria, y un campo en blanco es lo mismo que no tenerlo: el experimento corría y el informe salía con la sección «Hipótesis» vacía. **Corregí el código**: `_texto()` rechaza los obligatorios en blanco. Lo extendí a `objetivo.url` y `objetivo.contenedor`, que tenían el mismo agujero. | `test_un_campo_de_texto_obligatorio_vacio_lanza_error_configuracion`, 6 filas: cadena vacía y solo espacios por cada uno de los tres campos |

**Decisión:** 4 conservadas (con cambios de forma), 3 corregidas, 4 descartadas.

Lo que no cambió: **ninguna prueba se ajustó para que pasara**. Las dos que
fallaron por un defecto real (D-01 y D-02) se quedaron como estaban y lo que
cambió fue `caoslab/configuracion.py`. Las tres corregidas se corrigieron contra
el contrato del README, no contra lo que devolvía el código.

Sobre la redundancia: las semanas 5 y 6 ya tenían pruebas sueltas de varios de
estos casos (`test_estado_estable.py`, `test_motor.py`). No las borré porque
siguen documentando el contrato original y porque funcionan como segunda opinión
independiente de las tablas; en las mutaciones M1, M2, M3, M5, M7 y M8 cayeron
pruebas de los dos grupos. Lo que sí descarté del borrador fueron las pruebas que
no agregaban ninguna fila de mis tablas.

---

## 3. Romper el código a propósito

Ocho mutaciones, una a la vez, y la suite completa después de cada una. Después
de cada ejecución devolví el archivo a su estado original. Las ocho fueron
detectadas, así que no hizo falta agregar ningún caso nuevo.

| Cambio introducido | Archivo y línea | ¿Alguna prueba falló? | Qué hice |
|---|---|---|---|
| M1: `tasa_error > max` por `>=` | `estado_estable.py:89` | Sí, 5. Entre ellas `test_limites_de_la_tasa_de_error[18-2-0.1-0.1-CONTINUAR]` y `test_tabla_de_decision_del_estado_estable[R2-C1si-C2no-C3no]` | Nada: el borde inclusivo del ADR-002 queda protegido por las dos tablas y por la prueba de la semana 5 |
| M2: `ceil(0.95·n) − 1` por `int(0.95·n)` | `estado_estable.py:69` | Sí, 3: `test_el_p95_es_una_latencia_realmente_observada[20-19.0]` y `[40-38.0]`, más la del pico aislado de la semana 5 | Nada. Es el defecto real que tuve en la semana 5; ahora lo atrapan tres pruebas y no una |
| M3: `len(muestras) < minimo` por `<=` | `estado_estable.py:17` | Sí, 5: `test_limites_del_minimo_de_muestras[1-1-CONTINUAR]` y `[5-5-CONTINUAR]`, entre otras | Nada: el borde «exactamente el mínimo» está cubierto por los dos lados |
| M4: umbral de latencia con 10 % de holgura regalada (`max * 1.1`) | `estado_estable.py:94` | Sí, 1: `test_limites_de_la_latencia_p95[300.1-300.0-ABORTAR]` | Nada, pero es la mutación que menos pruebas mata: solo la atrapa el valor límite. Sin esa fila, un experimento habría podido pasarse un 10 % del presupuesto sin que nadie se enterara |
| M5: `ceil(duracion/ventana)` por `int(...)` | `motor.py:83` | Sí, 4: `test_limites_del_numero_de_ventanas[1-5-1]`, `[6-5-2]`, `[11-5-3]` y la de la semana 6 | Nada: con `int`, un experimento de 1 s no habría medido ninguna ventana |
| M6: `revertir()` despausa sin revisar el estado | `inyectores.py:39-40` | Sí, 1: `test_tabla_de_decision_de_revertir[True-running-0]` | Nada. Es la fila R3 de la tabla de decisión del inyector; sin ella, CaosLab podría despausar un contenedor que otra persona pausó a mano |
| M7: porcentaje con 0 decimales en vez de 2 | `informe.py:58` | Sí, 6: las 4 filas de `test_el_presupuesto_se_imprime_con_dos_decimales` y 2 de la semana 6 | Nada: con 0 decimales, un presupuesto de 0.4 % y uno de 0 % se verían iguales en el informe |
| M8: `campo <= 0` por `campo < 0` | `configuracion.py:70` | Sí, 6: las 5 filas `[0-False-*]` de `test_limites_de_los_campos_que_deben_ser_positivos` y la de la semana 6 | Nada: un `ventana_s: 0` habría llegado al motor y la división por cero habría reventado a mitad del experimento |

Cómo reproducirlo: `python herramientas/mutar.py` desde la raíz del repositorio.
El guion aplica cada mutación, corre la suite, imprime las pruebas que fallaron y
devuelve el archivo a su estado original; si alguna quedara a medias se deshace
con `git restore <archivo>`. Después de las ocho, `git status` quedó limpio salvo
por la corrección de D-01 y D-02 en `caoslab/configuracion.py`.

---

## 4. Datos de prueba

**Origen:** sintéticos, escritos a mano y después ampliados con IA (entrada 3 de
`bitacora_ia.md`). Están en `tests/conftest.py` como fixtures de pytest:
`catalogo_experimentos`, `fabricar_muestras`, `tanda_de_volumen` y
`escribir_experimento`.

**Confirmo que no hay datos de personas reales.** CaosLab no maneja personas: lo
que consume son nombres de contenedores, URLs, hipótesis y números. Los cuatro
servicios del catálogo imitan negocios del Huila para tener contexto local
(`caoslab-pedidos-db`, `caoslab-inventario-ñapa-db`, `caoslab-cafe-d'anita-web`, `caoslab-pagos-pse-api`) pero
ninguno corresponde a un negocio real, y todas las URLs apuntan a `localhost`.
No hay nombres de personas, ni teléfonos, ni correos, ni cédulas, ni los míos ni
los de mi familia.

**Casos difíciles incluidos:**

| Caso difícil | Dónde está | Qué prueba lo usa |
|---|---|---|
| Tildes | «caída de la réplica», `/menú`, `categoría=café` | `test_lee_tildes_ene_y_apostrofo_sin_romper_el_texto`, `test_el_informe_conserva_tildes_ene_y_apostrofo` |
| Ñ | `caoslab-inventario-ñapa-db`, «señal de inventario» | las mismas dos |
| Apóstrofo | `caoslab-cafe-d'anita-web`, «Café D'Anita» | las dos anteriores y `test_el_archivo_del_informe_se_guarda_en_utf8` |
| Texto vacío y solo espacios | `TEXTOS_VACIOS` del conftest | `test_un_campo_de_texto_obligatorio_vacio_lanza_error_configuracion` |
| Número en cero | latencia 0.0 ms, `max_tasa_error` 0.0, `duracion_s` 0 | `test_limites_de_la_latencia_p95[0.0-…]`, `test_limites_de_la_tasa_de_error[10-0-0.0-…]`, `test_limites_de_los_campos_que_deben_ser_positivos[0-False-*]` |
| Números negativos | latencias −0.1 y −1000, presupuestos −0.01 y −5 | `test_latencia_negativa_lanza_value_error_nombrando_la_muestra`, `test_presupuesto_invalido_lanza_value_error` |
| Texto donde va un número | `treinta`, `'30 s'` | `test_un_campo_numerico_con_texto_lanza_error_configuracion` |
| Volumen | 301 muestras: 285 exitosas, 15 fallidas y un pico de 9000 ms | `test_volumen_de_trescientas_muestras_con_un_pico_aislado` |
| UTF-8 en disco | informe guardado y vuelto a leer | `test_el_archivo_del_informe_se_guarda_en_utf8` |
