import math
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from caoslab.modelos import Muestra


class SondaHTTP:
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
        self._hilo.start()

    def recoger(self):
        with self._candado:
            muestras, self._muestras = self._muestras, []
        return muestras

    def detener(self):
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
