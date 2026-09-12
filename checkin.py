#!/usr/bin/env python3
"""Check-in PLC — versão terminal. Para a interface: python app.py"""

from __future__ import annotations

import sys

import gspread

from planilha import (
    COL_CHAMADO,
    COL_CHECKIN,
    COL_ESTACA,
    aba_da_estaca,
    abrir_planilha,
    ala_do_rotulo,
    atualizar_nome_planilha,
    carregar_linhas,
    carregar_todas,
    chamados_da_unidade,
    esta_marcado,
    filtrar,
    opcoes_unidade,
    registrar_checkin,
    rotulo_ala,
    unicos,
)


def escolher(titulo: str, opcoes: list[str]) -> str:
    if not opcoes:
        print(f"Nenhuma opção disponível para {titulo}.")
        sys.exit(1)

    print(f"\n=== {titulo} ===")
    for i, opcao in enumerate(opcoes, start=1):
        print(f"  {i}. {opcao}")

    while True:
        bruto = input(f"\nEscolha o número ({titulo}): ").strip()
        if not bruto.isdigit():
            print("Digite apenas o número da opção.")
            continue
        indice = int(bruto)
        if 1 <= indice <= len(opcoes):
            return opcoes[indice - 1]
        print(f"Opção inválida. Use um número de 1 a {len(opcoes)}.")


def pedir_nome() -> str:
    while True:
        novo = input("\nNovo nome completo: ").strip()
        if novo:
            return novo
        print("O nome não pode ficar vazio.")


def confirmar_registro() -> str:
    opcoes = {
        "1": "finalizar",
        "2": "renomear",
        "3": "recomeçar",
    }
    print("\n=== Confirmar ===")
    print("  1. É o registro certo — finalizar check-in")
    print("  2. Nome errado — alterar o nome")
    print("  3. Escolher de novo (chamado/estaca/ala errados)")
    while True:
        bruto = input("\nEscolha o número (Confirmar): ").strip()
        if bruto in opcoes:
            return opcoes[bruto]
        print("Opção inválida. Use 1, 2 ou 3.")


def selecionar_registro(linhas: list[dict]) -> dict | None:
    estaca = escolher(COL_ESTACA, unicos([l["estaca"] for l in linhas if l["estaca"]]))
    por_estaca = filtrar(linhas, estaca=estaca)

    unidade = escolher("Unidade", opcoes_unidade(por_estaca))
    ala = ala_do_rotulo(unidade)
    por_unidade = filtrar(por_estaca, ala=ala)

    chamados = chamados_da_unidade(por_unidade)
    if not chamados:
        print(
            f"\nTodo mundo de {unidade} já fez check-in."
            f"\nEm caso de dúvidas, procure a mesa da Estaca {estaca}."
        )
        return None

    rotulo = escolher(COL_CHAMADO, [c["rotulo"] for c in chamados])
    valor_chamado = next(c["valor"] for c in chamados if c["rotulo"] == rotulo)
    matches = filtrar(por_unidade, chamado=valor_chamado)
    if not matches:
        print("\nNenhuma linha encontrada com essa combinação.")
        return None

    if len(matches) > 1:
        nomes = [f"{l['nome']} — {l['chamado']}" for l in matches]
        escolhido = escolher("Pessoa (houve mais de um registro)", nomes)
        return matches[nomes.index(escolhido)]
    return matches[0]


def mostrar_registro(linha: dict) -> None:
    print(
        f"\nRegistro encontrado:\n"
        f"  Nome:    {linha['nome']}\n"
        f"  Chamado: {linha['chamado']}\n"
        f"  Estaca:  {linha['estaca']}\n"
        f"  Ala:     {rotulo_ala(linha['ala'])}"
    )


def fluxo_checkin(planilha) -> None:
    _colunas, linhas = carregar_todas(planilha)

    while True:
        linha = selecionar_registro(linhas)
        if not linha:
            continue

        aba = aba_da_estaca(planilha, linha["estaca"])
        colunas, _atual = carregar_linhas(aba)

        while True:
            mostrar_registro(linha)
            acao = confirmar_registro()

            if acao == "recomeçar":
                print("\nOk, vamos escolher de novo.")
                break

            if acao == "renomear":
                atualizar_nome_planilha(aba, linha, colunas, pedir_nome())
                print(f"Nome atualizado para: {linha['nome']}")
                continue

            valor_atual = aba.cell(linha["row"], colunas.index(COL_CHECKIN) + 1).value or ""
            if esta_marcado(valor_atual):
                print(f"\nErro: check-in já realizado para {linha['nome']}.")
                return

            registrar_checkin(aba, linha, colunas)
            print(f"\nCheck-in feito com sucesso para {linha['nome']}.")
            return


def main() -> None:
    print("Check-in PLC")
    planilha = abrir_planilha()

    while True:
        fluxo_checkin(planilha)
        outro = input("\nFazer outro check-in? [s/N]: ").strip().casefold()
        if outro not in {"s", "sim"}:
            print("Encerrado.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado.")
        sys.exit(0)
    except gspread.exceptions.APIError as exc:
        print(f"\nErro na API do Google Sheets: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(exc)
        sys.exit(1)
