import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Optional
import time

import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Dias da semana em português (weekday() → 0=segunda, 5=sábado)
DIAS_SEMANA = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
}

# Cache simples: evita chamar a API do Google a cada mensagem
_cache: dict = {"data": None, "timestamp": 0}
CACHE_TTL = 1800  # 30 minutos


def _get_sheet():
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(config.GOOGLE_SHEET_ID).sheet1


def _load_all_rows() -> list[dict]:
    """Carrega todas as linhas da planilha, usando cache de 30 min."""
    now = time.time()
    if _cache["data"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["data"]

    sheet = _get_sheet()
    rows = sheet.get_all_records()  # lista de dicts com cabeçalho como chave

    _cache["data"] = rows
    _cache["timestamp"] = now
    return rows


def get_dia_semana_hoje() -> Optional[str]:
    """Retorna o nome do dia atual (ex: 'Segunda'). None se for domingo."""
    return DIAS_SEMANA.get(datetime.now().weekday())


def get_pratos_do_dia(dia: Optional[str] = None) -> list[dict]:
    """
    Retorna lista com os pratos do dia informado (ou hoje se omitido).
    Cada item: {nome_prato, descricao, preco_pf, preco_marmita, foto_id}
    """
    if dia is None:
        dia = get_dia_semana_hoje()

    if dia is None:
        return []

    rows = _load_all_rows()

    pratos = []
    for row in rows:
        # Aceita variações de capitalização na planilha
        if str(row.get("dia_semana", "")).strip().lower() == dia.lower():
            pratos.append({
                "prato_numero": row.get("prato_numero", ""),
                "nome_prato":   str(row.get("nome_prato", "")).strip(),
                "descricao":    str(row.get("descricao", "")).strip(),
                "preco_pf":     _to_float(row.get("preco_pf")),
                "preco_marmita": _to_float(row.get("preco_marmita")),
                "foto_id":      str(row.get("foto_id", "")).strip(),
            })

    return pratos


def get_prato_por_nome(nome: str) -> Optional[dict]:
    """Busca um prato pelo nome (busca parcial, case-insensitive) em toda a planilha."""
    rows = _load_all_rows()
    nome_lower = nome.lower()

    for row in rows:
        if nome_lower in str(row.get("nome_prato", "")).lower():
            return {
                "dia_semana":   str(row.get("dia_semana", "")).strip(),
                "nome_prato":   str(row.get("nome_prato", "")).strip(),
                "descricao":    str(row.get("descricao", "")).strip(),
                "preco_pf":     _to_float(row.get("preco_pf")),
                "preco_marmita": _to_float(row.get("preco_marmita")),
                "foto_id":      str(row.get("foto_id", "")).strip(),
            }
    return None


def invalidar_cache():
    """Força recarga da planilha na próxima chamada."""
    _cache["data"] = None
    _cache["timestamp"] = 0


def _to_float(value) -> float:
    """Converte valor da célula para float, tratando vírgula como separador decimal."""
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0
