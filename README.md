# CaosLab

## 1. Qué es

CaosLab es un agente de pruebas de caos controlado para aplicaciones en Docker.
Mide cómo responde una aplicación, le inyecta un fallo (en esta entrega, pausar
un contenedor), vigila la salud del sistema por ventanas de tiempo y detiene el
experimento en cuanto el daño supera el presupuesto de error que el equipo
aceptó. Pase lo que pase, el fallo se revierte y queda un informe en markdown.

Es el proyecto final del Seminario de IA en Ingeniería de Software. Esta versión
cierra el primer incremento funcional (entrega 1, revisada en la semana 6).

Cómo decide el motor:

1. Mide la línea base. Si no da `CONTINUAR`, no inyecta nada: `LINEA_BASE_INESTABLE`.
2. Inyecta el fallo y evalúa cada ventana con `evaluar_estado_estable()`.
3. La primera ventana con `ABORTAR` detiene el experimento: `ABORTADO`.
4. Una ventana con pocas muestras no aborta. Si ninguna juntó evidencia: `SIN_EVIDENCIA`.
5. Si todas las ventanas pasan: `SUPERADO`.

`inyector.revertir()` está en un `finally`, y Ctrl+C, SIGTERM y Ctrl+Break piden
una parada ordenada. Si el proceso se mata a la fuerza, la siguiente corrida
encuentra el contenedor pausado y lo despausa.

**Límites de seguridad (semana 6).** CaosLab solo trabaja sobre la copia local:

- La sonda solo mide URL `http` o `https` hacia `localhost`, `127.0.0.1` o `::1`.
- Solo se pausan contenedores cuyo nombre empieza por `caoslab-`.
- Un experimento dura como máximo 120 s y la sonda manda como máximo 50 peticiones por segundo.

El contrato completo de `evaluar_estado_estable()` (HU-01) está en
[docs/contrato_hu01.md](docs/contrato_hu01.md) y el porqué de cada módulo en
[DOCUMENTACION.txt](DOCUMENTACION.txt).

## 2. Requisitos

- Python 3.11 o superior.
- Docker con Docker Compose (Docker Desktop en Windows y macOS), encendido, para
  correr experimentos y las pruebas de integración. Las pruebas unitarias no lo necesitan.
- Git.

Dependencias, con versión fijada en `requirements.txt`:

| Librería | Para qué |
|---|---|
| `PyYAML` | leer `experimento.yaml`; la librería estándar no lee YAML |
| `docker` | pausar y despausar el contenedor |
| `pytest` | pruebas |
| `ruff` | linter con reglas de estilo, errores y seguridad |
| `pip-audit` | buscar vulnerabilidades conocidas en las dependencias |

La sonda usa `urllib` de la librería estándar (ADR-001). FastAPI, uvicorn y
psycopg solo se instalan dentro de la imagen de la app demo (`app_demo/requirements.txt`).

## 3. Instalación

```bash
git clone https://github.com/Andresprov/CaosLab.git
cd CaosLab
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt  # instala también el comando caoslab
cp .env.example .env             # en Windows: copy .env.example .env
```

Abre `.env` y cambia `POSTGRES_PASSWORD` por una contraseña tuya (solo letras y
números, porque va dentro de una URL). `.env` no se sube al repositorio.

## 4. Ejecución

```bash
docker compose up -d --build     # app demo en http://localhost:8000 y su base de datos
caoslab run experimento.yaml     # corre el experimento
caoslab run experimento.yaml --informe otro_informe.md
docker compose down              # al terminar
```

El informe sale en consola y queda en `informe.md`.

| Código de salida | Significa |
|---|---|
| `0` | Superado: el sistema aguantó el fallo dentro del presupuesto. |
| `1` | Abortado, línea base inestable, sin evidencia o interrumpido. |
| `2` | Configuración inválida, contenedor inexistente o no permitido, o Docker apagado. |

`experimento.yaml`:

```yaml
nombre: pausa de la base de datos
hipotesis: >
  Si la base de datos queda congelada durante 30 segundos, la API de pedidos
  sigue respondiendo con menos de 5 % de errores y un p95 por debajo de 500 ms.
objetivo:
  url: http://localhost:8000/pedidos   # lo que mide la sonda (solo localhost)
  contenedor: caoslab-db               # lo que se pausa (debe empezar por caoslab-)
fallo:
  tipo: pausar                         # único tipo en esta entrega
duracion_s: 30                         # tiempo con el fallo inyectado, máximo 120
linea_base_s: 10                       # opcional, por defecto 10
ventana_s: 5                           # opcional, por defecto 5
peticiones_por_segundo: 5              # opcional, por defecto 5, máximo 50
timeout_s: 2                           # opcional, por defecto 2
presupuesto:
  max_tasa_error: 0.05
  max_latencia_p95_ms: 500
  minimo_muestras: 10                  # opcional, por defecto 1
```

Con la app demo esta hipótesis **no** se sostiene: el experimento aborta en la
primera ventana, que es lo que queremos ver. Con la URL `/health` se supera.

La app demo tiene dos contenedores: `caoslab-api` (FastAPI con `GET /health`,
`GET /pedidos` y `POST /pedidos`) y `caoslab-db` (PostgreSQL 16, sin puertos
fuera de la red de compose). Con la base pausada, `/pedidos` responde 503 en
unos 2 segundos y `/health` sigue normal.

## 5. Pruebas

```bash
pytest -m "not integracion"      # sin Docker: 234 pruebas (228 sin FastAPI instalado)
pytest -m integracion            # con Docker y la app demo levantada: 3 pruebas
pytest                           # todas
ruff check .                     # linter (configurado en pyproject.toml): sin avisos
pip-audit -r requirements.txt    # dependencias de CaosLab
pip-audit -r app_demo/requirements.txt
python herramientas/mutar.py     # las ocho mutaciones de la semana 7
```

`tests/test_app_demo.py` prueba la validación de `POST /pedidos` sin Docker,
pero necesita FastAPI: `pip install -r app_demo/requirements.txt httpx`. Si no
está instalado, pytest salta ese archivo.

| Archivo | Qué prueba | Docker |
|---|---|---|
| `test_estado_estable.py` | HU-01, las 12 pruebas originales | No |
| `test_configuracion.py` | lectura y validación de `experimento.yaml`, con pruebas de abuso | No |
| `test_inyectores.py` | pausar y revertir con un cliente Docker falso, contenedores no permitidos | Una sí |
| `test_reversion.py` | revertir ante excepción, Ctrl+C, KeyboardInterrupt y fallo al inyectar | No |
| `test_sonda.py` | sonda HTTP contra un servidor local | No |
| `test_motor.py` | línea base, ventanas, aborto y falta de evidencia | No |
| `test_informe.py` | contenido del informe | No |
| `test_cli.py` | comando `caoslab run` y sus códigos de salida | No |
| `test_app_demo.py` | validación de `POST /pedidos` | No |
| `test_extremo_a_extremo.py` | experimento completo contra la app demo | Sí |
| `test_semana7_estado_estable.py` | particiones, límites y tabla de decisión de HU-01 | No |
| `test_semana7_configuracion.py` | particiones y límites de `experimento.yaml` | No |
| `test_semana7_motor.py` | tabla de decisión de la conclusión y límites de las ventanas | No |
| `test_semana7_inyector.py` | estados del contenedor y tabla de decisión de `revertir()` | No |
| `test_semana7_informe.py` | el informe por conclusión, con datos sintéticos | No |
| `conftest.py` | datos de prueba sintéticos en fixtures | — |

Las pruebas de la semana 7 están diseñadas con particiones de equivalencia,
valores límite y tablas de decisión. El diseño completo, las pruebas generadas
con IA que corregí o descarté, las ocho mutaciones con las que rompí el código a
propósito y el origen de los datos sintéticos están en
[`registro_pruebas.md`](registro_pruebas.md). Para repetir las mutaciones:
`python herramientas/mutar.py`.

## 6. Estructura

```
CaosLab/
├── README.md
├── informe_final.md       # informe final del proyecto integrador
├── revision_seguridad.md   # informe de revisión de código y seguridad (semana 6)
├── registro_pruebas.md     # diseño de casos y revisión de las pruebas de IA (semana 7)
├── bitacora_ia.md          # registro de uso de IA
├── DOCUMENTACION.txt       # por qué cada parte del código está hecha así
├── LICENSE
├── pyproject.toml          # paquete, comando caoslab, pytest y ruff
├── requirements.txt        # versiones fijadas
├── .env.example            # copia como .env
├── .github/workflows/
│   └── ci.yml              # pipeline: ruff, pruebas, pip-audit e integración con Docker
├── herramientas/
│   └── mutar.py            # aplica una mutación, corre la suite y la deshace
├── docker-compose.yml      # app demo + PostgreSQL
├── experimento.yaml        # experimento de ejemplo
├── docs/
│   └── contrato_hu01.md    # contrato de evaluar_estado_estable()
├── app_demo/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # /health y /pedidos
├── caoslab/
│   ├── modelos.py          # Muestra, PresupuestoError, Veredicto, Estado
│   ├── estado_estable.py   # evaluar_estado_estable()
│   ├── configuracion.py    # lee y valida experimento.yaml
│   ├── inyectores.py       # Inyector (interfaz) e InyectorPausa
│   ├── sonda.py            # SondaHTTP en un hilo aparte
│   ├── motor.py            # ejecutar_experimento() y la reversión garantizada
│   ├── informe.py          # informe en markdown
│   └── cli.py              # caoslab run
└── tests/
```

## 7. Uso de IA

Usé Claude (Anthropic) como asistente en el chat y como agente de código. Cada
sugerencia está registrada en [bitacora_ia.md](bitacora_ia.md) con el prompt, la
decisión (aceptada, aceptada con cambios o rechazada), el porqué y cómo la verifiqué.

- Semana 5: la IA propuso la primera versión de `evaluar_estado_estable()`; las
  pruebas, escritas antes, atraparon un error en el cálculo del p95.
- Semana 6: la IA hizo una segunda revisión de seguridad; cada hallazgo se
  verificó ejecutando el código y se clasificó como real o falso positivo en
  [revision_seguridad.md](revision_seguridad.md). Un agente de código hizo las
  correcciones en la rama `semana-6-revision`, un commit por corrección, y su
  diff se revisó en un pull request antes de integrarlo.

Ninguna prueba se modificó para que pasara.

## 8. Autor y licencia

- **Autor:** Andrés David Trujillo
- **Asignatura:** Seminario de IA en Ingeniería de Software, FET
- **Docente:** Jorge Luis Trujillo Artunduaga

Licencia MIT; ver [LICENSE](LICENSE).
