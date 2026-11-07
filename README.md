# CaosLab

Agente de pruebas de caos controlado sobre una aplicación en Docker.

CaosLab inyecta fallos (latencia, caída de un contenedor, consumo de CPU) en un
entorno de pruebas y vigila la salud del sistema mientras el experimento corre.
Si el daño supera el presupuesto de error que el equipo definió, el experimento
se detiene y se revierte el fallo inyectado.

- **Estudiante:** Andrés David Trujillo
- **Asignatura:** Seminario de IA en Ingeniería de Software
- **Docente:** Jorge Luis Trujillo Artunduaga
- **Lenguaje:** Python 3.11+ · **Pruebas:** pytest

---

## Funcionalidad de la semana 5

### Historia de usuario

**HU-01 — Detener el experimento cuando se agota el presupuesto de error**
(prioridad: **Must**, documento de requisitos de la semana 3)

> Como ingeniero de confiabilidad,
> quiero que CaosLab evalúe el estado estable del sistema durante un experimento
> de caos y lo detenga cuando la tasa de error o la latencia superen el
> presupuesto acordado,
> para que un experimento no degrade el servicio más allá de lo que el equipo
> aceptó de antemano.

#### Criterio de aceptación

| Escenario | Dado | Cuando | Entonces |
|---|---|---|---|
| Sistema sano | un presupuesto de error y muestras dentro del umbral | se evalúa el estado estable | el veredicto es `CONTINUAR` y no hay motivos |
| Presupuesto agotado | muestras cuya tasa de error o latencia p95 supera el umbral | se evalúa el estado estable | el veredicto es `ABORTAR` y se indica cada motivo |
| Evidencia insuficiente | menos muestras que el mínimo exigido | se evalúa el estado estable | el veredicto es `MUESTRAS_INSUFICIENTES` y **no** se aborta |
| Dato inválido (error) | una muestra con latencia negativa o un presupuesto fuera de rango | se evalúa el estado estable | se lanza `ValueError` con un mensaje que nombra el dato inválido |

**Nota de diseño:** el umbral es **inclusivo**. Estar exactamente en el límite
todavía está dentro del presupuesto; solo se aborta al superarlo. Esta decisión
viene del ADR-002 del diseño de la semana 4 y es la razón de dos de las pruebas
de límite.

---

### Contrato de la función

```python
def evaluar_estado_estable(
    muestras: Sequence[Muestra],
    presupuesto: PresupuestoError,
) -> Veredicto
```

Módulo: `caoslab/estado_estable.py`

#### Qué recibe

| Parámetro | Tipo | Significado |
|---|---|---|
| `muestras` | `Sequence[Muestra]` | Observaciones tomadas durante la ventana del experimento, en cualquier orden. |
| `presupuesto` | `PresupuestoError` | Límites que el equipo aceptó antes de inyectar el fallo. |

```python
@dataclass(frozen=True)
class Muestra:
    exitosa: bool        # True si la petición respondió correctamente
    latencia_ms: float   # latencia observada, en milisegundos (>= 0)

@dataclass(frozen=True)
class PresupuestoError:
    max_tasa_error: float        # fracción de error tolerada, en [0.0, 1.0]
    max_latencia_p95_ms: float   # latencia p95 tolerada, en ms (> 0)
    minimo_muestras: int = 1     # muestras mínimas para emitir un veredicto (>= 1)
```

#### Qué devuelve

```python
@dataclass(frozen=True)
class Veredicto:
    estado: Estado                # CONTINUAR | ABORTAR | MUESTRAS_INSUFICIENTES
    tasa_error: float             # fallidas / total, 0.0 si no hay muestras
    latencia_p95_ms: float        # percentil 95 por rango más cercano, 0.0 si no hay muestras
    motivos: tuple[str, ...]      # vacío salvo cuando el estado es ABORTAR
```

La función es **pura**: no lee reloj, no escribe en disco, no toca la red y no
muta las `muestras` que recibe. Por eso se puede probar sin levantar Docker.

#### Supuestos

- Las muestras pertenecen a una sola ventana de observación de un solo experimento.
- El orden de llegada no importa: el p95 se calcula sobre las latencias ordenadas.
- El percentil 95 se calcula por el **método de rango más cercano**:
  `indice = ceil(0.95 * n) - 1` sobre las latencias ordenadas de menor a mayor.
  Con pocas muestras este método no interpola, devuelve siempre una latencia
  realmente observada.
- La tasa de error y la latencia se evalúan de forma independiente: basta con que
  una supere su umbral para abortar, y el veredicto lista **todos** los motivos.

#### Casos límite

| Caso | Comportamiento |
|---|---|
| `muestras` vacía | `MUESTRAS_INSUFICIENTES`, con `tasa_error = 0.0` y `latencia_p95_ms = 0.0`. Nunca aborta: sin evidencia no se toma una decisión destructiva. |
| Menos muestras que `minimo_muestras` | `MUESTRAS_INSUFICIENTES`, aunque todas hayan fallado. |
| Una sola muestra | El p95 es la latencia de esa muestra. |
| Tasa de error exactamente igual a `max_tasa_error` | `CONTINUAR` (umbral inclusivo). |
| Latencia p95 exactamente igual a `max_latencia_p95_ms` | `CONTINUAR` (umbral inclusivo). |
| Un único pico aislado de latencia en 20 muestras | No mueve el p95: el pico queda por encima del percentil y el experimento continúa. |
| `max_tasa_error` igual a `0.0` | Válido: cualquier fallo agota el presupuesto. |

#### Casos de error

| Entrada inválida | Excepción |
|---|---|
| Alguna `Muestra` con `latencia_ms` negativa | `ValueError` |
| `max_tasa_error` fuera de `[0.0, 1.0]` | `ValueError` |
| `max_latencia_p95_ms` menor o igual a `0` | `ValueError` |
| `minimo_muestras` menor que `1` | `ValueError` |

#### Ejemplos de entrada y salida

**Ejemplo 1 — el sistema aguanta el fallo inyectado**

```python
muestras = [Muestra(exitosa=True, latencia_ms=120.0)] * 10
presupuesto = PresupuestoError(max_tasa_error=0.05, max_latencia_p95_ms=300.0)

evaluar_estado_estable(muestras, presupuesto)
# Veredicto(estado=Estado.CONTINUAR, tasa_error=0.0,
#           latencia_p95_ms=120.0, motivos=())
```

**Ejemplo 2 — se agota el presupuesto de error**

```python
muestras = [Muestra(exitosa=False, latencia_ms=90.0)] * 3 + \
           [Muestra(exitosa=True,  latencia_ms=90.0)] * 7
presupuesto = PresupuestoError(max_tasa_error=0.10, max_latencia_p95_ms=300.0)

evaluar_estado_estable(muestras, presupuesto)
# Veredicto(estado=Estado.ABORTAR, tasa_error=0.3, latencia_p95_ms=90.0,
#           motivos=('tasa de error 30.00% supera el máximo de 10.00%',))
```

**Ejemplo 3 — todavía no hay evidencia suficiente**

```python
evaluar_estado_estable([], PresupuestoError(0.05, 300.0, minimo_muestras=5))
# Veredicto(estado=Estado.MUESTRAS_INSUFICIENTES, tasa_error=0.0,
#           latencia_p95_ms=0.0, motivos=())
```

**Ejemplo 4 — dato inválido**

```python
evaluar_estado_estable(
    [Muestra(exitosa=True, latencia_ms=-1.0)],
    PresupuestoError(0.05, 300.0),
)
# ValueError: la muestra 0 tiene una latencia negativa: -1.0 ms
```

---

## Entrega 1: esqueleto caminante

Un experimento de caos completo, de principio a fin, con un solo tipo de fallo:
pausar un contenedor. CaosLab mide la línea base, pausa el contenedor, vigila la
app por ventanas con `evaluar_estado_estable()` y aborta en cuanto el veredicto
es `ABORTAR`. Pase lo que pase, el contenedor vuelve a quedar corriendo.

### Cómo correr un experimento

Necesitas Docker encendido y Python 3.11 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt  # instala también el comando caoslab

docker compose up -d --build     # levanta la app demo y su base de datos
caoslab run experimento.yaml
```

El informe sale en consola y queda guardado en `informe.md` (se puede cambiar
con `--informe otra_ruta.md`).

| Código de salida | Significa |
|---|---|
| `0` | Experimento superado: el sistema aguantó el fallo dentro del presupuesto. |
| `1` | Abortado, línea base inestable, sin evidencia suficiente o interrumpido. |
| `2` | Configuración inválida, contenedor inexistente o Docker apagado. |

### La app demo

`docker-compose.yml` levanta dos contenedores:

- `caoslab-api`: FastAPI en `http://localhost:8000` con `GET /health` (no toca
  la base) y `GET /pedidos` / `POST /pedidos` (sí la tocan).
- `caoslab-db`: PostgreSQL 16. No expone puertos fuera de la red de compose y
  usa autenticación `trust`, así que no hay contraseñas ni `.env`.

Cuando la base está pausada, `/pedidos` responde 503 en unos 2 segundos y
`/health` sigue respondiendo normal.

### experimento.yaml

```yaml
nombre: pausa de la base de datos
hipotesis: >
  Si la base de datos queda congelada durante 30 segundos, la API de pedidos
  sigue respondiendo con menos de 5 % de errores y un p95 por debajo de 500 ms.
objetivo:
  url: http://localhost:8000/pedidos   # lo que mide la sonda
  contenedor: caoslab-db               # lo que se pausa
fallo:
  tipo: pausar                         # único tipo en esta entrega
duracion_s: 30                         # tiempo con el fallo inyectado
linea_base_s: 10                       # opcional, por defecto 10
ventana_s: 5                           # opcional, por defecto 5
peticiones_por_segundo: 5              # opcional, por defecto 5
timeout_s: 2                           # opcional, por defecto 2
presupuesto:
  max_tasa_error: 0.05
  max_latencia_p95_ms: 500
  minimo_muestras: 10                  # opcional, por defecto 1
```

Con la app demo esta hipótesis **no** se sostiene: el experimento aborta en la
primera ventana, que es justo lo que queremos ver. Si cambias la URL a
`/health`, el experimento se supera.

### Cómo decide el motor

1. Mide la línea base. Si no da `CONTINUAR` (ya está fuera del presupuesto o no
   juntó muestras suficientes), no inyecta nada: `LINEA_BASE_INESTABLE`.
2. Inyecta el fallo y evalúa cada ventana con las muestras de esa ventana.
3. La primera ventana con `ABORTAR` detiene el experimento: `ABORTADO`.
4. Una ventana con `MUESTRAS_INSUFICIENTES` no aborta. Si ninguna juntó
   evidencia, el resultado es `SIN_EVIDENCIA` y no `SUPERADO`.
5. Si todas las ventanas pasan: `SUPERADO`.

### Reversión garantizada

- `inyector.revertir()` está en un `finally`: corre si el experimento termina
  bien, si aborta, si salta una excepción o si llega un `KeyboardInterrupt`.
- Ctrl+C (SIGINT), SIGTERM y Ctrl+Break (SIGBREAK, en Windows) no matan el
  proceso: piden una parada ordenada, el motor sale del ciclo en menos de 0.2 s,
  revierte y deja el informe con `INTERRUMPIDO`.
- Lo único que ningún código puede atrapar es matar el proceso a la fuerza
  (`kill -9`, `taskkill /F`, apagar la máquina). Para eso, al empezar cada
  corrida CaosLab revisa si el contenedor objetivo quedó pausado y, si es así,
  lo despausa y lo avisa en consola.

Todo esto se verificó contra Docker real: Ctrl+Break con la base pausada deja
el contenedor en `running`; `taskkill /F` lo deja en `paused` y la siguiente
corrida lo recupera.

### Pendiente para la entrega 2

- Otros tipos de fallo: latencia de red, consumo de CPU y matar el contenedor.
  El motor ya trabaja contra la interfaz `Inyector` (`inyectar()` y
  `revertir()`), así que solo hay que agregar clases nuevas.
- Hipótesis generadas con IA.
- Informe en HTML.
- Histórico de experimentos.
- Panel web.
- Integración con CI.

---

## Cómo ejecutar las pruebas

```bash
pytest                          # todas (necesita Docker y la app levantada)
pytest -m "not integracion"     # sin Docker: 64 pruebas
pytest -m integracion           # solo las que usan Docker real: 3 pruebas
```

| Archivo | Qué prueba | Docker |
|---|---|---|
| `test_estado_estable.py` | HU-01, las 12 pruebas originales | No |
| `test_configuracion.py` | lectura y validación de `experimento.yaml` | No |
| `test_inyectores.py` | pausar y revertir con un cliente Docker falso, y una con el real | Una sí |
| `test_reversion.py` | revertir ante excepción, Ctrl+C, KeyboardInterrupt y fallo al inyectar | No |
| `test_sonda.py` | sonda HTTP contra un servidor local en un hilo | No |
| `test_motor.py` | línea base, ventanas, aborto y falta de evidencia | No |
| `test_informe.py` | contenido del informe | No |
| `test_cli.py` | comando `caoslab run` y sus códigos de salida | No |
| `test_extremo_a_extremo.py` | experimento completo contra la app demo | Sí |

Las pruebas del motor usan un inyector y una sonda falsos en memoria
(`tests/falsos.py`).

---

## Estructura del repositorio

```
caoslab/
├── README.md
├── DOCUMENTACION.txt       # explicación de cada parte del código
├── bitacora_ia.md
├── pyproject.toml          # comando caoslab y marcador integracion
├── requirements.txt
├── docker-compose.yml      # app demo + PostgreSQL
├── experimento.yaml        # experimento de ejemplo
├── app_demo/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # /health y /pedidos
├── caoslab/
│   ├── modelos.py          # Muestra, PresupuestoError, Veredicto, Estado
│   ├── estado_estable.py   # evaluar_estado_estable() (semana 5)
│   ├── configuracion.py    # lee experimento.yaml
│   ├── inyectores.py       # Inyector (interfaz) e InyectorPausa
│   ├── sonda.py            # SondaHTTP en un hilo aparte
│   ├── motor.py            # ejecutar_experimento() y la reversión garantizada
│   ├── informe.py          # informe en markdown
│   └── cli.py              # caoslab run
└── tests/
```

## Dependencias

| Librería | Para qué |
|---|---|
| `PyYAML` | leer `experimento.yaml`; la librería estándar no lee YAML |
| `docker` | pausar y despausar el contenedor |
| `pytest` | pruebas |

La sonda usa `urllib` de la librería estándar, así se respeta el ADR-001.
FastAPI, uvicorn y psycopg solo se instalan dentro de la imagen de la app demo.

## Historial de commits de la semana 5

| Momento | Mensaje |
|---|---|
| Pruebas en rojo | `test: pruebas del estado estable del experimento (en rojo)` |
| Implementación | `feat: evalúa el estado estable con el asistente (1 prueba en rojo)` |
| Pruebas en verde | `fix: calcula el p95 por rango más cercano (todas las pruebas en verde)` |
| Refactorización | `refactor: separa validación, métricas y motivos en el estado estable` |
| Documentación | `docs: contrato en el README y bitácora de uso de IA` |

Los commits de la entrega 1 se ven con `git log`: cada paso tiene su commit de pruebas en rojo y su commit de implementación en verde.
