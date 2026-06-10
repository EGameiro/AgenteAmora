# Agente Restaurante Python — "Amora 🍓"

Agente de atendimento via WhatsApp para restaurantes. Recebe mensagens pelo webhook da UAZAPI, processa com Claude (Haiku), consulta cardápio no Google Sheets e gerencia pedidos em memória.

---

## Stack

| Camada | Tecnologia |
|---|---|
| LLM | Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) |
| Web server | FastAPI + Uvicorn |
| WhatsApp | UAZAPI (webhook + envio de texto/imagem) |
| Cardápio | Google Sheets via gspread |
| Fotos | GitHub raw (pasta `fotos/` no repositório) |
| HTTP client | httpx (async) |
| Python | 3.11 |

---

## Estrutura

```
.
├── main.py                        → FastAPI: webhook /webhook + health GET /
├── agent.py                       → Loop Claude com tool calling
├── config.py                      → Variáveis de ambiente via python-dotenv
├── mise.toml                      → Configuração do mise (Python 3.11.9, sem attestations)
├── nixpacks.toml                  → Configuração de build para Railway
├── Procfile                       → Comando de start para Railway
├── prompts/
│   └── system_prompt.txt          → Persona e regras da Amora
├── services/
│   ├── session_service.py         → Sessões em memória por telefone (TTL 4h)
│   ├── order_service.py           → Carrinho: ItemPedido + Carrinho
│   ├── sheets_service.py          → Google Sheets com cache 30 min
│   ├── media_service.py           → URLs de foto via GitHub raw
│   └── google_credentials.py     → Carrega credenciais Google (arquivo ou env var)
├── fotos/                         → Imagens dos pratos (PNG/JPG) hospedadas no repo
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
    ↓  body: { EventType, message: { sender_pn, text, senderName, fromMe, ... } }
main.py  →  extrai telefone, texto, nome
    ↓
agent.processar_mensagem(telefone, texto, nome)
    ↓
session_service  →  get_ou_criar(telefone)  →  Sessao (estado + carrinho + histórico)
    ↓
agent._chamar_claude(sessao)  →  loop: Claude → tool_use → executar_tool → Claude
    ↓
sheets_service / order_service  →  resultados das tools
    ↓
resposta_texto + lista de (url_foto, legenda)
    ↓
main.py  →  enviar_texto()  →  enviar_imagem_url() por foto  →  UAZAPI  →  WhatsApp
```

### Primeira mensagem de cada sessão
Ao detectar `estado == INICIO`, o `agent.py`:
1. Busca os pratos do dia no Google Sheets
2. Coleta URLs das fotos (GitHub raw) com legenda `nome + preços`
3. Injeta no histórico uma instrução para o Claude se apresentar pelo nome do cliente
4. Avança o estado para `CARDAPIO`
5. O `main.py` envia o texto primeiro e as fotos em seguida

---

## Configuração (.env)

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google Sheets — ID na URL da planilha (entre /d/ e /edit)
GOOGLE_SHEET_ID=1AbCdEfGhIjKlMnOpQrStUvWxYz
GOOGLE_CREDENTIALS_FILE=credentials/google_service_account.json
# Alternativa para produção (Railway): conteúdo JSON da service account como string
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}

# UAZAPI
UAZAPI_BASE_URL=https://sua-instancia.uazapi.com
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
| Quarta | 1 | Picanha Suína Grelhada | ... | 22.90 | 20.50 | Picanha Suina.png |

- `dia_semana`: Segunda, Terça, Quarta, Quinta, Sexta, Sábado (domingo = sem pratos)
- `preco_pf` / `preco_marmita`: aceita vírgula ou ponto como separador decimal
- `foto_id`: nome exato do arquivo na pasta `fotos/` do repositório (ex: `Picanha Suina.png`)

A planilha deve ser compartilhada com a service account:
`agente-amora@agente-restaurante-499018.iam.gserviceaccount.com` (permissão Editor)

**Cache:** a planilha é recarregada a cada 30 minutos. Para forçar recarga: `sheets_service.invalidar_cache()`.

---

## Fotos dos Pratos

As imagens ficam na pasta `fotos/` do repositório GitHub. O `media_service` monta a URL raw:

```
https://raw.githubusercontent.com/EGameiro/AgenteAmora/master/fotos/{nome_arquivo}
```

- Formatos aceitos: JPG, PNG
- O nome do arquivo na pasta deve ser igual ao `foto_id` na planilha
- Espaços no nome são codificados automaticamente via `urllib.parse.quote`
- Cada foto é enviada com legenda: `Nome do Prato\nPF: R$ X | Marmita: R$ Y`

---

## Sessões

- Armazenadas **em memória** (`dict` global em `session_service.py`)
- TTL: **4 horas** sem atividade → sessão expira, próxima mensagem inicia nova apresentação
- Cada sessão contém: `telefone`, `estado` (enum), `carrinho` (Carrinho), `historico`, `data_criacao`

### Estados (`Estado` enum)

| Estado | Quando entra |
|---|---|
| `INICIO` | Primeira mensagem (sessão nova ou expirada) |
| `CARDAPIO` | Após enviar pratos do dia |
| `PEDINDO` | Ao adicionar o primeiro item |
| `UPSELL` | (disponível para uso futuro) |
| `FECHAMENTO` | (disponível para uso futuro) |
| `CONCLUIDO` | Ao registrar forma de pagamento |

---

## Webhook UAZAPI — Formato do Payload

```json
{
  "EventType": "messages",
  "message": {
    "sender_pn": "5511992846459@s.whatsapp.net",
    "senderName": "Eduardo",
    "text": "ola",
    "fromMe": false,
    "isGroup": false,
    "wasSentByApi": false
  },
  "chat": {
    "wa_name": "Eduardo"
  }
}
```

### Endpoints UAZAPI utilizados

| Ação | Endpoint | Payload |
|---|---|---|
| Enviar texto | `POST /send/text` | `{"number": "55...", "text": "..."}` |
| Enviar imagem | `POST /send/media` | `{"number": "55...", "type": "image", "file": "url", "text": "legenda"}` |

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

## Deploy no Railway

1. Conectar repositório GitHub no Railway
2. Configurar variáveis de ambiente:

| Variável | Descrição |
|---|---|
| `ANTHROPIC_API_KEY` | Chave da API Anthropic |
| `GOOGLE_SHEET_ID` | ID da planilha Google Sheets |
| `GOOGLE_CREDENTIALS_JSON` | Conteúdo JSON da service account (em uma linha) |
| `UAZAPI_BASE_URL` | URL base da instância UAZAPI |
| `UAZAPI_TOKEN` | Token de autenticação UAZAPI |
| `UAZAPI_INSTANCE` | Nome da instância UAZAPI |

3. O Railway detecta o `nixpacks.toml` e usa Python 3.11 via nix
4. O `mise.toml` desativa verificação de attestations do GitHub
5. URL gerada pelo Railway usar como webhook na UAZAPI: `https://seu-app.railway.app/webhook`

**Atenção:** sessões ficam em memória — reiniciar o processo encerra todos os pedidos em andamento.

---

## Extensões Futuras

- Persistência de sessões (Redis ou SQLite) para sobreviver a reinícios
- Salvar pedidos finalizados no Google Sheets ou banco de dados
- Suporte a áudio (transcrição via Whisper)
- Múltiplos restaurantes (multi-tenant via número UAZAPI)
- Notificação para a cozinha ao finalizar pedido
