import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from caoslab.sonda import SondaHTTP


class Manejador(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/lento":
            time.sleep(1)
        codigo = 500 if self.path == "/error" else 200
        self.send_response(codigo)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


class ServidorSilencioso(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass


@pytest.fixture
def servidor():
    servidor = ServidorSilencioso(("127.0.0.1", 0), Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()
    servidor.server_close()


def correr(url, segundos, peticiones_por_segundo=20, timeout_s=2):
    sonda = SondaHTTP(url, peticiones_por_segundo, timeout_s)
    sonda.iniciar()
    time.sleep(segundos)
    sonda.detener()
    return sonda.recoger()


def test_una_respuesta_200_es_una_muestra_exitosa_con_su_latencia(servidor):
    muestras = correr(f"{servidor}/ok", 0.5)

    assert len(muestras) >= 5
    assert all(m.exitosa for m in muestras)
    assert all(0 <= m.latencia_ms < 1000 for m in muestras)


def test_una_respuesta_500_es_una_muestra_fallida(servidor):
    muestras = correr(f"{servidor}/error", 0.3)

    assert muestras
    assert not any(m.exitosa for m in muestras)


def test_una_peticion_que_supera_el_timeout_es_fallida_y_registra_el_tiempo_esperado(servidor):
    muestras = correr(f"{servidor}/lento", 0.2, peticiones_por_segundo=10, timeout_s=0.3)

    assert muestras
    assert not any(m.exitosa for m in muestras)
    assert all(m.latencia_ms >= 250 for m in muestras)


def test_si_no_hay_servidor_las_muestras_son_fallidas():
    muestras = correr("http://127.0.0.1:9/", 0.3, timeout_s=0.5)

    assert muestras
    assert not any(m.exitosa for m in muestras)


def test_mantiene_el_ritmo_aunque_las_peticiones_se_demoren(servidor):
    muestras = correr(f"{servidor}/lento", 1.0, peticiones_por_segundo=10, timeout_s=0.3)

    assert len(muestras) >= 8


def test_iniciar_no_bloquea_porque_la_sonda_corre_en_otro_hilo(servidor):
    sonda = SondaHTTP(f"{servidor}/lento", 5, 2)

    inicio = time.perf_counter()
    sonda.iniciar()
    tardo = time.perf_counter() - inicio
    sonda.detener()

    assert tardo < 0.1


def test_recoger_entrega_las_muestras_nuevas_y_vacia_el_buffer(servidor):
    sonda = SondaHTTP(f"{servidor}/ok", 20, 2)
    sonda.iniciar()
    time.sleep(0.3)
    primeras = sonda.recoger()
    sonda.detener()
    segundas = sonda.recoger()

    assert primeras
    assert len(segundas) < len(primeras)
    assert sonda.recoger() == []


def test_despues_de_detener_ya_no_produce_muestras(servidor):
    sonda = SondaHTTP(f"{servidor}/ok", 20, 2)
    sonda.iniciar()
    time.sleep(0.2)
    sonda.detener()
    sonda.recoger()
    time.sleep(0.3)

    assert sonda.recoger() == []
