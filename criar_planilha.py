"""
Cria (ou recria) a planilha do cardápio no Google Sheets com dados de exemplo.
Uso: python criar_planilha.py

Após rodar, o script imprime o ID da planilha — copie para o .env como GOOGLE_SHEET_ID.
IMPORTANTE: compartilhe a planilha com o e-mail da Service Account como Editor.
"""

import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
CABECALHO = [
    "dia_semana",
    "prato_numero",
    "nome_prato",
    "descricao",
    "preco_pf",
    "preco_marmita",
    "foto_id",
]

# ---------------------------------------------------------------------------
# Dados de exemplo — substitua pelos pratos reais depois
# foto_id = ID do arquivo no Google Drive (parte final da URL de compartilhamento)
# ---------------------------------------------------------------------------
DADOS = [
    # Segunda
    ["Segunda", 1, "Frango Grelhado com Legumes",
     "Filé de frango grelhado temperado com ervas finas, acompanha arroz branco, feijão, salada de alface e tomate e farofa.",
     18.90, 16.50, "ID_FOTO_SEGUNDA_PRATO1"],
    ["Segunda", 2, "Carne Assada ao Molho",
     "Carne bovina assada lentamente ao molho de cebola e alho, acompanha arroz, feijão, macarrão e salada.",
     20.90, 18.50, "ID_FOTO_SEGUNDA_PRATO2"],

    # Terça
    ["Terça", 1, "Tilápia Frita",
     "Filé de tilápia empanado e frito, temperado com limão e alho, acompanha arroz, feijão, purê de batata e salada.",
     19.90, 17.50, "ID_FOTO_TERCA_PRATO1"],
    ["Terça", 2, "Frango à Parmegiana",
     "Frango empanado com molho de tomate caseiro e queijo derretido, acompanha arroz, feijão e batata frita.",
     21.90, 19.50, "ID_FOTO_TERCA_PRATO2"],

    # Quarta
    ["Quarta", 1, "Picanha Suína Grelhada",
     "Picanha suína grelhada na chapa com tempero especial da casa, acompanha arroz, feijão, mandioca frita e vinagrete.",
     22.90, 20.50, "ID_FOTO_QUARTA_PRATO1"],
    ["Quarta", 2, "Macarrão à Bolonhesa",
     "Macarrão espaguete ao molho bolonhesa com carne moída temperada, acompanha arroz, salada e pão de alho.",
     18.90, 16.50, "ID_FOTO_QUARTA_PRATO2"],

    # Quinta
    ["Quinta", 1, "Feijoada Completa",
     "Feijoada tradicional com carne seca, linguiça, paio e costelinha, acompanha arroz, couve refogada, farofa e laranja.",
     24.90, 22.50, "ID_FOTO_QUINTA_PRATO1"],
    ["Quinta", 2, "Filé de Frango ao Limão",
     "Filé de frango ao molho de limão siciliano com alcaparras, acompanha arroz integral, feijão e salada verde.",
     19.90, 17.50, "ID_FOTO_QUINTA_PRATO2"],

    # Sexta
    ["Sexta", 1, "Bacalhau à Portuguesa",
     "Bacalhau desfiado com batatas, ovos cozidos, azeitonas e azeite extravirgem, acompanha arroz e salada.",
     26.90, 24.50, "ID_FOTO_SEXTA_PRATO1"],
    ["Sexta", 2, "Frango Xadrez",
     "Frango salteado com pimentões coloridos, milho e amendoim torrado ao molho shoyu, acompanha arroz branco.",
     20.90, 18.50, "ID_FOTO_SEXTA_PRATO2"],

    # Sábado
    ["Sábado", 1, "Churrasco Misto",
     "Combinação de picanha, linguiça artesanal e frango grelhados na brasa, acompanha arroz, farofa e vinagrete.",
     29.90, 27.50, "ID_FOTO_SABADO_PRATO1"],
    ["Sábado", 2, "Moqueca de Peixe",
     "Moqueca tradicional baiana com filé de peixe branco, leite de coco, tomate, pimentão e coentro, acompanha arroz e pirão.",
     27.90, 25.50, "ID_FOTO_SABADO_PRATO2"],
]


def main():
    print("Conectando ao Google Sheets...")
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    # Cria nova planilha
    print("Criando planilha 'Cardápio Restaurante'...")
    spreadsheet = client.create("Cardápio Restaurante")
    sheet = spreadsheet.sheet1
    sheet.update_title("Cardapio")

    # Formata cabeçalho
    sheet.append_row(CABECALHO)

    # Insere dados
    sheet.append_rows(DADOS)

    # Ajusta largura das colunas (aproximado via número de caracteres)
    larguras = [100, 100, 200, 500, 100, 120, 300]
    requests = []
    for i, largura in enumerate(larguras):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": largura},
                "fields": "pixelSize",
            }
        })
    spreadsheet.batch_update({"requests": requests})

    # Congela cabeçalho
    spreadsheet.batch_update({
        "requests": [{
            "updateSheetProperties": {
                "properties": {"sheetId": sheet.id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        }]
    })

    sheet_id = spreadsheet.id
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

    print()
    print("=" * 60)
    print("✅ Planilha criada com sucesso!")
    print(f"   URL: {sheet_url}")
    print(f"   ID:  {sheet_id}")
    print()
    print("📌 Próximos passos:")
    print("   1. Copie o ID acima para o .env como GOOGLE_SHEET_ID")
    print("   2. Abra a planilha e substitua os 'ID_FOTO_*' pelos IDs")
    print("      reais dos arquivos no Google Drive")
    print("   3. Compartilhe a planilha com o e-mail da Service Account")
    print(f"      (encontrado no arquivo {config.GOOGLE_CREDENTIALS_FILE})")
    print("=" * 60)


if __name__ == "__main__":
    main()
