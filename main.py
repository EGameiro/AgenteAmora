import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio

import config
import agent

app = FastAPI(title="Agente A Amora")

# ---------------------------------------------------------------------------
# Envio de mensagens via UAZAPI
# ---------------------------------------------------------------------------
HEADERS = {
    "token": config.UAZAPI_TOKEN,
    "Content-Type": "application/json",
}

async def enviar_texto(telefone: str, texto: str):
    url = f"{config.UAZAPI_BASE_URL}/message/sendText/{config.UAZAPI_INSTANCE}"
    payload = {"phone": telefone, "message": texto}
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=payload, headers=HEADERS)


async def enviar_imagem_url(telefone: str, url_imagem: str, legenda: str = ""):
    url = f"{config.UAZAPI_BASE_URL}/message/sendImage/{config.UAZAPI_INSTANCE}"
    payload = {"phone": telefone, "image": url_imagem, "caption": legenda}
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=payload, headers=HEADERS)


# ---------------------------------------------------------------------------
# Webhook — recebe mensagens do WhatsApp via UAZAPI
# ---------------------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    # Ignora mensagens enviadas pelo próprio bot
    if body.get("fromMe"):
        return JSONResponse({"status": "ignored"})

    # Extrai telefone e texto
    telefone = body.get("phone") or body.get("from", "")
    texto = (
        body.get("text")
        or body.get("body")
        or body.get("message", {}).get("conversation", "")
        or ""
    ).strip()

    if not telefone or not texto:
        return JSONResponse({"status": "ignored"})

    # Processa com o agente (síncrono em thread separada para não bloquear)
    resposta, fotos = await asyncio.get_event_loop().run_in_executor(
        None, agent.processar_mensagem, telefone, texto
    )

    # Envia fotos primeiro (pratos do dia na abertura)
    for url_foto in fotos:
        await enviar_imagem_url(telefone, url_foto)

    # Envia resposta em texto
    if resposta:
        await enviar_texto(telefone, resposta)

    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
def health():
    return {"status": "online", "agente": "A Amora 🍓"}
