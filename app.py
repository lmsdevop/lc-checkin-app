#!/usr/bin/env python3
"""Interface web do Check-in PLC. Uso: python app.py"""

from __future__ import annotations

import socket
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from planilha import (
    aba_da_estaca,
    abrir_planilha,
    ala_do_rotulo,
    atualizar_chamado_planilha,
    atualizar_nome_planilha,
    carregar_linhas,
    carregar_por_estaca,
    carregar_todas,
    chamados_da_unidade,
    esta_marcado,
    filtrar,
    opcoes_unidade,
    pendentes,
    registrar_checkin,
    serializar,
    unicos,
    valor_checkin,
)

app = Flask(__name__)
_planilha = None


def planilha():
    global _planilha
    if _planilha is None:
        _planilha = abrir_planilha(quiet=True)
    return _planilha


def contexto(estaca: str | None = None):
    if estaca:
        return carregar_por_estaca(planilha(), estaca)
    return carregar_todas(planilha())


def encontrar(linhas: list[dict], row: int) -> dict | None:
    for linha in linhas:
        if linha["row"] == row:
            return linha
    return None


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/opcoes")
def api_opcoes():
    chamado = (request.args.get("chamado") or "").strip() or None
    estaca = (request.args.get("estaca") or "").strip() or None
    ala_param = request.args.get("ala")

    try:
        _colunas, linhas = contexto(estaca)
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 404

    por_estaca = linhas
    por_unidade = filtrar(por_estaca, ala=ala_do_rotulo(ala_param)) if estaca and ala_param is not None else por_estaca

    registros = []
    if chamado and estaca and ala_param is not None:
        registros = [serializar(l) for l in pendentes(filtrar(por_unidade, chamado=chamado))]

    return jsonify(
        {
            "estacas": unicos([l["estaca"] for l in pendentes(linhas) if l["estaca"]]),
            "unidades": opcoes_unidade(por_estaca) if estaca else [],
            "chamados": chamados_da_unidade(por_unidade) if estaca and ala_param is not None else [],
            "registros": registros,
        }
    )


@app.post("/api/checkin")
def api_checkin():
    dados = request.get_json(silent=True) or {}
    row = dados.get("row")
    estaca = (dados.get("estaca") or "").strip()
    if not isinstance(row, int) or not estaca:
        return jsonify({"ok": False, "erro": "Registro inválido."}), 400

    try:
        ws = aba_da_estaca(planilha(), estaca)
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 404
    colunas, linhas = carregar_linhas(ws)
    linha = encontrar(linhas, row)
    if not linha:
        return jsonify({"ok": False, "erro": "Registro não encontrado."}), 404

    if esta_marcado(valor_checkin(ws, linha, colunas)):
        return jsonify({"ok": False, "erro": f"Check-in já realizado para {linha['nome']}."}), 409

    registrar_checkin(ws, linha, colunas)
    return jsonify(
        {
            "ok": True,
            "registro": serializar(linha),
            "hora": datetime.now().strftime("%H:%M"),
        }
    )


@app.post("/api/nome")
def api_nome():
    dados = request.get_json(silent=True) or {}
    row = dados.get("row")
    estaca = (dados.get("estaca") or "").strip()
    nome = (dados.get("nome") or "").strip()
    if not isinstance(row, int) or not nome or not estaca:
        return jsonify({"ok": False, "erro": "Informe um nome válido."}), 400

    try:
        ws = aba_da_estaca(planilha(), estaca)
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 404
    colunas, linhas = carregar_linhas(ws)
    linha = encontrar(linhas, row)
    if not linha:
        return jsonify({"ok": False, "erro": "Registro não encontrado."}), 404

    atualizar_nome_planilha(ws, linha, colunas, nome)
    return jsonify({"ok": True, "registro": serializar(linha)})


@app.post("/api/chamado")
def api_chamado():
    dados = request.get_json(silent=True) or {}
    row = dados.get("row")
    estaca = (dados.get("estaca") or "").strip()
    chamado = (dados.get("chamado") or "").strip()
    if not isinstance(row, int) or not chamado or not estaca:
        return jsonify({"ok": False, "erro": "Informe um chamado válido."}), 400

    try:
        ws = aba_da_estaca(planilha(), estaca)
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 404
    colunas, linhas = carregar_linhas(ws)
    linha = encontrar(linhas, row)
    if not linha:
        return jsonify({"ok": False, "erro": "Registro não encontrado."}), 404

    try:
        atualizar_chamado_planilha(ws, linha, colunas, chamado)
    except ValueError as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 400

    return jsonify({"ok": True, "registro": serializar(linha)})


def ip_local() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


if __name__ == "__main__":
    porta = 5050
    lan = ip_local()
    print("Check-in PLC")
    print(f"  Neste computador: http://127.0.0.1:{porta}")
    print(f"  No celular (mesma Wi-Fi): http://{lan}:{porta}")
    app.run(host="0.0.0.0", port=porta, debug=False)
