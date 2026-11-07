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

## Cómo ejecutar las pruebas

```bash
git clone <url-del-repositorio>
cd caoslab

python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest
```

Un solo comando (`pytest`) ejecuta las 12 pruebas desde la raíz del repositorio.
Para ver el nombre de cada una:

```bash
pytest -v
```

### Cobertura de las pruebas

| Tipo | Pruebas |
|---|---|
| Casos normales (3) | sistema sano con todas las peticiones correctas; tasa de error que agota el presupuesto; tasa y latencia fuera de umbral a la vez (dos motivos) |
| Casos límite (6) | tasa de error exactamente en el umbral; p95 exactamente en el umbral; lista vacía; una sola muestra; menos muestras que el mínimo; pico aislado en 20 muestras |
| Casos de error (3) | latencia negativa; `max_tasa_error` fuera de rango; `minimo_muestras` inválido |

---

## Estructura del repositorio

```
caoslab/
├── README.md               # este archivo: historia, contrato y cómo probar
├── bitacora_ia.md          # bitácora de uso del asistente de IA
├── requirements.txt        # pytest
├── .gitignore              # ignora .env, .venv, __pycache__
├── caoslab/
│   ├── __init__.py
│   ├── modelos.py          # Muestra, PresupuestoError, Veredicto, Estado
│   └── estado_estable.py   # evaluar_estado_estable(): la funcionalidad de la semana 5
└── tests/
    └── test_estado_estable.py
```

## Historial de commits de esta entrega

| Momento | Mensaje |
|---|---|
| Pruebas en rojo | `test: pruebas del estado estable del experimento (en rojo)` |
| Implementación | `feat: evalúa el estado estable con el asistente (1 prueba en rojo)` |
| Pruebas en verde | `fix: calcula el p95 por rango más cercano (todas las pruebas en verde)` |
| Refactorización | `refactor: separa validación, métricas y motivos en el estado estable` |
| Documentación | `docs: contrato en el README y bitácora de uso de IA` |
