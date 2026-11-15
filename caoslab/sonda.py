import math
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from caoslab.modelos import Muestra


class SondaHTTP:
    """Mide una URL a ritmo constante en un hilo aparte y guarda una Muestra por petición.

    Una respuesta 2xx o 3xx es exitosa; un error HTTP, un timeout o una conexión
    rechazada cuentan como fallidas. Ignora los proxies del sistema.

    Recibe:
        url: dirección a medir.
        peticiones_por_segundo: ritmo de las peticiones.
        timeout_s: segundos máximos de espera por petición.
    """

    def __init__(self, url, peticiones_por_segundo, timeout_s):
        self.url = url
        self.intervalo = 1 / peticiones_por_segundo
        self.timeout_s = timeout_s
        self._muestras = []
        self._candado = threading.Lock()
        self._parar = threading.Event()
        self._abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self._trabajadores = ThreadPoolExecutor(max_workers=math.ceil(peticiones_por_segundo * timeout_s) + 2)
        self._hilo = threading.Thread(target=self._disparar, name="sonda-http", daemon=True)

    def iniciar(self):
        """Arranca el hilo que dispara las peticiones. Solo se puede llamar una vez (RuntimeError si se repite)."""
        self._hilo.start()

    def recoger(self):
        """Devuelve las muestras acumuladas desde la última llamada y vacía la lista."""
        with self._candado:
            muestras, self._muestras = self._muestras, []
        return muestras

    def detener(self):
        """Para de disparar peticiones y espera a que terminen las que estaban en curso."""
        self._parar.set()
        if self._hilo.is_alive():
            self._hilo.join()
        self._trabajadores.shutdown(wait=True)

    def _disparar(self):
        siguiente = time.monotonic()
        while not self._parar.is_set():
            self._trabajadores.submit(self._medir)
            siguiente += self.intervalo
            self._parar.wait(max(0, siguiente - time.monotonic()))

    def _medir(self):
        inicio = time.perf_counter()
        try:
            with self._abridor.open(self.url, timeout=self.timeout_s) as respuesta:
                respuesta.read()
                exitosa = 200 <= respuesta.status < 400
        except (urllib.error.URLError, OSError):
            exitosa = False
        latencia_ms = (time.perf_counter() - inicio) * 1000
        with self._candado:
            self._muestras.append(Muestra(exitosa, latencia_ms))
