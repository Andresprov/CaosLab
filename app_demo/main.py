import os
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

URL_BD = os.environ["URL_BD"]


class PedidoNuevo(BaseModel):
    producto: str
    cantidad: int


def conectar():
    return psycopg.connect(URL_BD, connect_timeout=1)


def preparar_tabla():
    with conectar() as conexion:
        conexion.execute(
            "CREATE TABLE IF NOT EXISTS pedidos ("
            "id SERIAL PRIMARY KEY, producto TEXT NOT NULL, cantidad INT NOT NULL)"
        )
        total = conexion.execute("SELECT count(*) FROM pedidos").fetchone()[0]
        if total == 0:
            conexion.execute(
                "INSERT INTO pedidos (producto, cantidad) VALUES "
                "('teclado', 2), ('monitor', 1), ('mouse', 3)"
            )


@asynccontextmanager
async def ciclo_de_vida(app):
    preparar_tabla()
    yield


app = FastAPI(title="App demo de CaosLab", lifespan=ciclo_de_vida)


@app.get("/health")
def health():
    return {"estado": "ok"}


@app.get("/pedidos")
def listar_pedidos():
    try:
        with conectar() as conexion:
            filas = conexion.execute(
                "SELECT id, producto, cantidad FROM pedidos ORDER BY id"
            ).fetchall()
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="base de datos no disponible")
    return [{"id": i, "producto": p, "cantidad": c} for i, p, c in filas]


@app.post("/pedidos", status_code=201)
def crear_pedido(pedido: PedidoNuevo):
    try:
        with conectar() as conexion:
            nuevo_id = conexion.execute(
                "INSERT INTO pedidos (producto, cantidad) VALUES (%s, %s) RETURNING id",
                (pedido.producto, pedido.cantidad),
            ).fetchone()[0]
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="base de datos no disponible")
    return {"id": nuevo_id, "producto": pedido.producto, "cantidad": pedido.cantidad}
