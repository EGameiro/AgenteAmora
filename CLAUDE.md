# Agente Restaurante Python — "A Amora 🍓"

Agente de atendimento via WhatsApp para restaurantes. Recebe mensagens pelo webhook da UAZAPI, processa com Claude (Haiku), consulta cardápio no Google Sheets e gerencia pedidos em memória.

---

## Stack

| Camada | Tecnologia |
|---|---|
| LLM | Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) |
| Web server | FastAPI + Uvicorn |
| WhatsApp | UAZAPI (webhook + envio de texto/imagem) |
| Cardápio | Google Sheets via gspread |
| Fotos | Google Drive (URLs públicas) |
| HTTP client | httpx (async) |
| Python | 3.11 |

---

## Estrutura

```
.
├── main.py                        → FastAPI: webhook /webhook + health GET /
├── agent.py                       → Loop Claude com tool calling
├── config.py                      → Variáveis de ambiente via python-dotenv
├── prompts/
│   └── system_prompt.txt          → Persona e regras da Amora
├── services/
│   ├── session_service.py         → Sessões em memória por telefone (TTL 4h)
│   ├── order_service.py           → Carrinho: ItemPedido + Carrinho
│   ├── sheets_service.py          → Google Sheets com cache 30 min
│   └── media_service.py           → URLs de foto via Google Drive
├── cardapio_exemplo.csv           → Modelo de planilha (não usado em runtime)
├── criar_planilha.py              → Script utilitário para popular a planilha
├── teste_cli.py                   → Teste local sem WhatsApp
├── .env                           → Variáveis de ambiente (não versionar)
├── .env.example                   → Template das variáveis
├── requirements.txt
└── credentials/
    └── google_service_account.json  → Credencial da service account (não versionar)
```

---

## Fluxo de Dados

```
WhatsApp (cliente)
    ↓  POST /webhook
UAZAPI
    ↓  body: { phone, text, fromMe, ... }
main.py  →  agent.processar_mensagem(telefone, texto)
    ↓
session_service  →  get_ou_criar(telefone)  →  Sessao (estado + carrinho + histórico)
    ↓
agent._chamar_claude(sessao)  →  loop: Claude → tool_use → executar_tool → Claude
    ↓
sheets_service / order_service  →  resultados das tools
    ↓
resposta_texto + lista de URLs de fotos
    ↓
main.py  →  enviar_imagem_url() + enviar_texto()  →  UAZAPI  →  WhatsApp
```

### Primeira mensagem de cada sessão
Ao detectar `estado == INICIO`, o `agent.py` busca os pratos do dia e coleta as URLs das fotos para envio antes do texto. O estado avança para `CARDAPIO`.

---

## Configuração (.env)

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Sheets — ID na URL da planilha
GOOGLE_SHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz
GOOGLE_CREDENTIALS_FILE=credentials/google_service_account.json

# UAZAPI
UAZAPI_BASE_URL=https://api.uazapi.dev
UAZAPI_TOKEN=seu_token_aqui
UAZAPI_INSTANCE=nome_da_instancia

# App
PORT=8000
```

---

## Google Sheets — Formato da Planilha

A planilha deve ter **exatamente estes cabeçalhos** na primeira linha (Sheet1):

| dia_semana | prato_numero | nome_prato | descricao | preco_pf | preco_marmita | foto_id |
|---|---|---|---|---|---|---|
| Segunda | 1 | Frango Grelhado | ... | 18.90 | 16.50 | ID_DO_DRIVE |

- `dia_semana`: Segunda, Terça, Quarta, Quinta, Sexta, Sábado (domingo = sem pratos)
- `preco_pf` / `preco_marmita`: aceita vírgula ou ponto como separador decimal
- `foto_id`: ID do arquivo no Google Drive (parte da URL após `/d/`)

**Cache:** a planilha é recarregada a cada 30 minutos. Para forçar recarga: `sheets_service.invalidar_cache()`.

---

## Google Drive — Fotos

As imagens dos pratos devem estar no Google Drive com compartilhamento **"Qualquer pessoa com o link pode ver"**. O `media_service` monta a URL direta:

```
https://drive.google.com/uc?export=view&id={foto_id}
```

---

## Sessões

- Armazenadas **em memória** (`dict` global em `session_service.py`)
- TTL: **4 horas** sem atividade → sessão expirada e recriada na próxima mensagem
- Cada sessão contém: `telefone`, `estado` (enum), `carrinho` (Carrinho), `historico` (lista de mensagens para o Claude)

### Estados (`Estado` enum)

| Estado | Quando entra |
|---|---|
| `INICIO` | Primeira mensagem (sessão nova) |
| `CARDAPIO` | Após enviar pratos do dia |
| `PEDINDO` | Ao adicionar o primeiro item |
| `UPSELL` | (disponível para uso futuro) |
| `FECHAMENTO` | (disponível para uso futuro) |
| `CONCLUIDO` | Ao registrar forma de pagamento |

---

## Tools do Agente (Function Calling)

| Tool | Descrição |
|---|---|
| `get_pratos_do_dia` | Retorna pratos do dia atual (nome, preços, foto_id) |
| `get_descricao_prato` | Descrição detalhada de um prato pelo nome (busca parcial) |
| `adicionar_item` | Adiciona prato ao carrinho (tipo: `pf` ou `marmita`) |
| `remover_item` | Remove prato do carrinho |
| `ver_carrinho` | Resumo do pedido com total formatado |
| `registrar_pagamento` | Registra forma de pagamento e marca sessão como `CONCLUIDO` |

Formas de pagamento aceitas: `Dinheiro`, `Cartão de Débito`, `Cartão de Crédito`, `PIX`.

---

## Carrinho (`order_service.py`)

- Incrementa quantidade automaticamente se o mesmo prato+tipo já existe
- `resumo_texto()` retorna texto formatado com emojis para envio direto ao cliente
- `total()` arredonda para 2 casas decimais

---

## Rodando Localmente

```bash
# 1. Criar ambiente virtual e instalar dependências
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Configurar variáveis
cp .env.example .env
# editar .env com suas credenciais

# 3. Iniciar servidor
uvicorn main:app --reload --port 8000

# 4. Expor com ngrok (para receber webhook do UAZAPI)
ngrok.exe http 8000

# 5. Testar sem WhatsApp (CLI)
python teste_cli.py
```

---

## Deploy

O servidor é um processo Python simples (FastAPI + Uvicorn). Pode ser hospedado em:
- **VPS/Linux**: `uvicorn main:app --host 0.0.0.0 --port 8000` + systemd ou supervisor
- **Railway / Render / Fly.io**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **ngrok**: apenas para desenvolvimento (não persistente)

**Atenção:** sessões ficam em memória — reiniciar o processo encerra todos os pedidos em andamento.

---

## Extensões Futuras

- Persistência de sessões (Redis ou SQLite) para sobreviver a reinícios
- Salvar pedidos finalizados no Google Sheets ou banco de dados
- Suporte a áudio (transcrição via Whisper)
- Múltiplos restaurantes (multi-tenant via número UAZAPI)
- Notificação para a cozinha ao finalizar pedido
