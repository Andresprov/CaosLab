"""Pruebas de abuso de la app demo (semana 6).

Necesitan fastapi y httpx instalados (pip install -r app_demo/requirements.txt httpx).
Si no están, pytest las salta. No necesitan Docker ni la base de datos: el cliente
de pruebas no ejecuta el arranque de la app, así que /pedidos responde 503.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv("URL_BD", "postgresql://caoslab:x@127.0.0.1:1/pedidos")
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent / "app_demo"))
    sys.modules.pop("main", None)
    import main

    return TestClient(main.app)


@pytest.mark.parametrize(
    "pedido",
    [
        {"producto": "teclado", "cantidad": -5},
        {"producto": "teclado", "cantidad": 0},
        {"producto": "teclado", "cantidad": 1_000_000},
        {"producto": "", "cantidad": 1},
        {"producto": "x" * 5000, "cantidad": 1},
    ],
)
def test_rechaza_pedidos_con_datos_fuera_de_rango(cliente, pedido):
    assert cliente.post("/pedidos", json=pedido).status_code == 422


def test_un_pedido_valido_pasa_la_validacion_y_llega_a_la_base(cliente):
    assert cliente.post("/pedidos", json={"producto": "teclado", "cantidad": 2}).status_code == 503


