from __future__ import annotations

import json
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SHEET_ID = "1z1QjJGWOaxboPOFUDmk5CC-5kkDdqT1bcWl8lL_B_fs"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
OAUTH_PORT = 8080
PASTA = Path(__file__).resolve().parent
CREDENTIALS_FILE = PASTA / "credentials.json"
TOKEN_FILE = PASTA / "authorized_user.json"
SEM_ALA = "Estaca"
UNIDADE_ESTACA = "Estaca"
COL_NOME = "Nome Completo"
COL_CHAMADO = "Chamado"
COL_ESTACA = "Estaca"
COL_ALA = "Ala"
COL_CHECKIN = "Check In"
COL_QRCODE = "Via QRCode"
INSTRUCOES_OAUTH = """
Arquivo credentials.json não encontrado (ou está no formato errado).

Como gerar o login da sua conta:
  1. https://console.cloud.google.com/ → crie um projeto
  2. Ative a API: Google Sheets API
  3. APIs e serviços → Tela de consentimento OAuth
     Tipo: Externo → adicione SEU e-mail em Usuários de teste
  4. APIs e serviços → Credenciais → Criar credenciais
     → ID do cliente OAuth → Aplicativo para computador (ou Web)
  5. Se for Web, em URIs de redirecionamento autorizados adicione:
     http://localhost:8080/
  6. Baixe o JSON e salve como:
     {caminho}

Não use "conta de serviço".
""".format(caminho=CREDENTIALS_FILE)


def _json_env(nome: str) -> dict | None:
    bruto = (os.environ.get(nome) or "").strip()
    if not bruto:
        return None
    return json.loads(bruto)


def _json_arquivo(caminho: Path) -> dict | None:
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text())


def dados_credenciais() -> dict | None:
    return _json_env("GOOGLE_CREDENTIALS") or _json_arquivo(CREDENTIALS_FILE)


def dados_token() -> dict | None:
    return _json_env("GOOGLE_TOKEN") or _json_arquivo(TOKEN_FILE)


def credenciais_sao_oauth() -> bool:
    try:
        dados = dados_credenciais() or {}
    except json.JSONDecodeError:
        return False
    return "installed" in dados or "web" in dados


def autenticar(quiet: bool = False) -> Credentials:
    creds = None
    token = dados_token()
    if token:
        creds = Credentials.from_authorized_user_info(token, SCOPES)

    if creds and creds.valid:
        if not quiet:
            print("Usando login já salvo.")
        return creds

    if creds and creds.expired and creds.refresh_token:
        if not quiet:
            print("Renovando login salvo...")
        creds.refresh(Request())
        if not os.environ.get("GOOGLE_TOKEN"):
            TOKEN_FILE.write_text(creds.to_json())
        return creds

    cliente = dados_credenciais()
    if not cliente:
        print(INSTRUCOES_OAUTH)
        sys.exit(1)

    if not quiet:
        print("Abrindo o navegador para login na sua conta Google...")
        print(f"Se aparecer redirect_uri_mismatch, cadastre http://localhost:{OAUTH_PORT}/ no cliente OAuth.")
    flow = InstalledAppFlow.from_client_config(cliente, SCOPES)
    creds = flow.run_local_server(port=OAUTH_PORT, prompt="consent")
    TOKEN_FILE.write_text(creds.to_json())
    return creds


def abrir_planilha(quiet: bool = False):
    if not credenciais_sao_oauth():
        print(INSTRUCOES_OAUTH)
        sys.exit(1)

    client = gspread.authorize(autenticar(quiet=quiet))
    return client.open_by_key(SHEET_ID)


def chave_estaca(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", nome or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def aba_da_estaca(planilha, estaca: str):
    alvo = chave_estaca(estaca)
    for ws in planilha.worksheets():
        if chave_estaca(ws.title) == alvo:
            return ws
    raise ValueError(f"Aba da estaca '{estaca}' não encontrada.")


def normalizar(valor: str) -> str:
    return (valor or "").strip()


def esta_marcado(valor: str) -> bool:
    """A coluna Check In é uma caixa de seleção: desmarcada devolve FALSE."""
    return normalizar(str(valor)).casefold() not in {"", "false", "0", "não", "nao", "n"}


def unicos(valores: list[str]) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for valor in valores:
        if valor not in vistos:
            vistos.add(valor)
            resultado.append(valor)
    return sorted(resultado, key=str.casefold)


def rotulo_ala(ala: str) -> str:
    return ala if ala else SEM_ALA


ORDEM_ORGANIZACOES = [
    "Presidência da Estaca",
    "Bispado / Ramo",
    "Quórum de Élderes",
    "Sociedade de Socorro",
    "Moças",
    "Primária",
    "Outros",
]

ROTULOS_CHAMADO = {
    "Presidente das Moças": "Presidente das Moças da Ala",
    "Presidente da Primária": "Presidente da Primária da Ala",
    "Presidente da Sociedade de Socorro": "Presidente da Sociedade de Socorro da Ala",
    "Presidente do Quórum de Élderes": "Presidente do Quórum de Élderes da Ala",
}


def organizacao_do_chamado(chamado: str) -> str:
    c = chamado.casefold()
    if "moças" in c or "mocas" in c:
        return "Moças"
    if "primária" in c or "primaria" in c:
        return "Primária"
    if "sociedade de socorro" in c:
        return "Sociedade de Socorro"
    if "élderes" in c or "elderes" in c:
        return "Quórum de Élderes"
    if "bispo" in c or "bispado" in c or "ramo" in c:
        return "Bispado / Ramo"
    if "presidente da estaca" in c or "conselheiro da estaca" in c:
        return "Presidência da Estaca"
    return "Outros"


GRUPOS_SUBSTITUICAO = {
    "Bispado": ("Bispo", "1º Conselheiro do Bispado", "2º Conselheiro do Bispado"),
    "Ramo": ("Presidente de Ramo", "1º Conselheiro do Ramo", "2º Conselheiro do Ramo"),
    "Quórum de Élderes": (
        "Presidente do Quórum de Élderes",
        "1º Conselheiro do Quórum de Élderes",
        "2º Conselheiro do Quórum de Élderes",
    ),
    "Sociedade de Socorro": (
        "Presidente da Sociedade de Socorro",
        "1ª Conselheira da Sociedade de Socorro",
        "2ª Conselheira da Sociedade de Socorro",
    ),
    "Moças": (
        "Presidente das Moças",
        "1ª Conselheira das Moças",
        "2ª Conselheira das Moças",
    ),
    "Primária": (
        "Presidente da Primária",
        "1ª Conselheira da Primária",
        "2ª Conselheira da Primária",
    ),
}


def e_chamado_de_estaca(chamado: str) -> bool:
    c = chamado.casefold()
    return " da estaca" in c or organizacao_do_chamado(chamado) == "Presidência da Estaca"


def grupo_substituicao(chamado: str) -> str | None:
    if e_chamado_de_estaca(chamado):
        return None
    c = chamado.casefold()
    if "bispo" in c or "bispado" in c:
        return "Bispado"
    if "ramo" in c:
        return "Ramo"
    if "élderes" in c or "elderes" in c:
        return "Quórum de Élderes"
    if "moças" in c or "mocas" in c:
        return "Moças"
    if "primária" in c or "primaria" in c:
        return "Primária"
    if "sociedade de socorro" in c:
        return "Sociedade de Socorro"
    return None


def opcoes_substituicao(chamado: str) -> list[dict]:
    grupo = grupo_substituicao(chamado)
    if not grupo:
        return []
    lider, cons1, cons2 = GRUPOS_SUBSTITUICAO[grupo]
    atual = chamado.strip()
    opcoes = []
    for valor in (lider, cons1, cons2):
        opcoes.append(
            {
                "valor": valor,
                "rotulo": f"{valor} (Atual)" if valor.casefold() == atual.casefold() else valor,
                "atual": valor.casefold() == atual.casefold(),
            }
        )
    return opcoes


def rotulo_chamado(chamado: str) -> str:
    return ROTULOS_CHAMADO.get(chamado, chamado)


def ordem_chamado(chamado: str) -> tuple:
    c = chamado.casefold()
    if "1ª" in chamado or "1º" in chamado:
        faixa = 2
    elif "2ª" in chamado or "2º" in chamado:
        faixa = 3
    elif " da estaca" in c:
        faixa = 1
    else:
        faixa = 0
    return (faixa, c)


def organizacoes_presentes(linhas: list[dict]) -> list[str]:
    presentes = {organizacao_do_chamado(l["chamado"]) for l in linhas if l["chamado"]}
    return [org for org in ORDEM_ORGANIZACOES if org in presentes]


def chamados_da_organizacao(linhas: list[dict], organizacao: str) -> list[dict]:
    valores = unicos(
        [l["chamado"] for l in linhas if l["chamado"] and organizacao_do_chamado(l["chamado"]) == organizacao]
    )
    valores.sort(key=ordem_chamado)
    return [{"valor": c, "rotulo": rotulo_chamado(c)} for c in valores]


def pendentes(linhas: list[dict]) -> list[dict]:
    return [l for l in linhas if not esta_marcado(l["checkin"])]


def chamados_da_unidade(linhas: list[dict]) -> list[dict]:
    valores = unicos([l["chamado"] for l in pendentes(linhas) if l["chamado"]])
    valores.sort(key=ordem_chamado)
    return [{"valor": c, "rotulo": rotulo_chamado(c)} for c in valores]


def opcoes_unidade(linhas: list[dict]) -> list[str]:
    opcoes = []
    if any(not l["ala"] for l in linhas):
        opcoes.append(UNIDADE_ESTACA)
    opcoes.extend([a for a in unicos([l["ala"] for l in linhas]) if a])
    return opcoes


def _intervalo_aba(titulo: str) -> str:
    return f"'{titulo.replace(chr(39), chr(39) * 2)}'"


def parse_linhas(estaca: str, valores: list[list[str]]) -> tuple[list[str], list[dict]]:
    if not valores:
        raise ValueError(f"A aba '{estaca}' está vazia.")

    cabecalhos = [normalizar(h) for h in valores[0]]
    obrigatorios = [COL_NOME, COL_CHAMADO, COL_ALA, COL_CHECKIN]
    faltando = [c for c in obrigatorios if c not in cabecalhos]
    if not _coluna_qrcode(cabecalhos):
        faltando.append(COL_QRCODE)
    if faltando:
        raise ValueError(f"Colunas não encontradas na aba '{estaca}': {', '.join(faltando)}")

    idx = {nome: cabecalhos.index(nome) for nome in obrigatorios}
    linhas = []
    for numero, row in enumerate(valores[1:], start=2):
        def celula(col: str) -> str:
            i = idx[col]
            return normalizar(row[i] if i < len(row) else "")

        nome = celula(COL_NOME)
        chamado = celula(COL_CHAMADO)
        if not nome and not chamado:
            continue
        linhas.append(
            {
                "row": numero,
                "nome": nome,
                "chamado": chamado,
                "estaca": estaca,
                "ala": celula(COL_ALA),
                "checkin": celula(COL_CHECKIN),
            }
        )
    return cabecalhos, linhas


def carregar_linhas(ws) -> tuple[list[str], list[dict]]:
    return parse_linhas(ws.title, ws.get_all_values())


def carregar_todas(planilha) -> tuple[list[str], list[dict]]:
    abas = planilha.worksheets()
    if not abas:
        raise ValueError("Nenhuma aba de estaca válida foi encontrada.")

    resposta = planilha.values_batch_get([_intervalo_aba(ws.title) for ws in abas])
    linhas = []
    colunas: list[str] = []
    for ws, bloco in zip(abas, resposta.get("valueRanges", [])):
        try:
            cabecalhos, parte = parse_linhas(ws.title, bloco.get("values") or [])
        except ValueError:
            continue
        if not colunas:
            colunas = cabecalhos
        linhas.extend(parte)
    if not linhas:
        raise ValueError("Nenhuma aba de estaca válida foi encontrada.")
    return colunas, linhas


def carregar_por_estaca(planilha, estaca: str) -> tuple[list[str], list[dict]]:
    return carregar_linhas(aba_da_estaca(planilha, estaca))


def filtrar(linhas: list[dict], chamado: str | None = None, estaca: str | None = None, ala: str | None = None) -> list[dict]:
    resultado = linhas
    if chamado:
        resultado = [l for l in resultado if l["chamado"] == chamado]
    if estaca:
        alvo = chave_estaca(estaca)
        resultado = [l for l in resultado if chave_estaca(l["estaca"]) == alvo]
    if ala is not None:
        resultado = [l for l in resultado if l["ala"] == ala]
    return resultado


def opcoes_ala(linhas: list[dict]) -> list[str]:
    opcoes = []
    if any(not l["ala"] for l in linhas):
        opcoes.append(SEM_ALA)
    opcoes.extend([a for a in unicos([l["ala"] for l in linhas]) if a])
    return opcoes


def ala_do_rotulo(rotulo: str) -> str:
    return "" if rotulo in {SEM_ALA, UNIDADE_ESTACA} else rotulo


def serializar(linha: dict) -> dict:
    substituicoes = opcoes_substituicao(linha["chamado"])
    return {
        "row": linha["row"],
        "nome": linha["nome"],
        "chamado": linha["chamado"],
        "estaca": linha["estaca"],
        "ala": linha["ala"],
        "ala_rotulo": rotulo_ala(linha["ala"]),
        "checkin": esta_marcado(linha["checkin"]),
        "pode_alterar_chamado": bool(substituicoes),
        "opcoes_chamado": substituicoes,
    }


def _coluna_qrcode(cabecalhos: list[str]) -> str | None:
    aliases = {COL_QRCODE.casefold(), "via qr code", "via qrcode"}
    for nome in cabecalhos:
        if nome.casefold() in aliases:
            return nome
    return None


def agora() -> datetime:
    return datetime.now(FUSO)


def texto_via_qrcode() -> str:
    return agora().strftime("Sim - %d/%m %H:%M:%S")


def registrar_checkin(ws, linha: dict, colunas: list[str]) -> None:
    nome_qr = _coluna_qrcode(colunas)
    if nome_qr is None:
        raise ValueError(f"Coluna {COL_QRCODE} não encontrada na planilha.")
    ws.update_cell(linha["row"], colunas.index(COL_CHECKIN) + 1, "TRUE")
    ws.update_cell(linha["row"], colunas.index(nome_qr) + 1, texto_via_qrcode())


def atualizar_nome_planilha(ws, linha: dict, colunas: list[str], novo: str) -> None:
    ws.update_cell(linha["row"], colunas.index(COL_NOME) + 1, novo)
    linha["nome"] = novo


def atualizar_chamado_planilha(ws, linha: dict, colunas: list[str], novo: str) -> None:
    permitidos = {opcao["valor"] for opcao in opcoes_substituicao(linha["chamado"])}
    if novo not in permitidos:
        raise ValueError("Esse chamado não pode ser alterado para essa opção.")
    ws.update_cell(linha["row"], colunas.index(COL_CHAMADO) + 1, novo)
    linha["chamado"] = novo


def valor_checkin(ws, linha: dict, colunas: list[str]) -> str:
    return ws.cell(linha["row"], colunas.index(COL_CHECKIN) + 1).value or ""
