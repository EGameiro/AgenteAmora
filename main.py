import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import logging
import traceback

import config
import agent

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Agente A Amora")

# ---------------------------------------------------------------------------
# Envio de mensagens via UAZAPI
# ---------------------------------------------------------------------------
HEADERS = {
    "token": config.UAZAPI_TOKEN,
    "Content-Type": "application/json",
}

async def enviar_texto(telefone: str, texto: str):
    url = f"{config.UAZAPI_BASE_URL}/send/text"
    numero = telefone.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("+", "").strip()
    payload = {"number": numero, "text": texto}
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(url, json=payload, headers=HEADERS)


async def enviar_imagem_url(telefone: str, url_imagem: str, legenda: str = ""):
    url = f"{config.UAZAPI_BASE_URL}/send/media"
    numero = telefone.replace("@s.whatsapp.net", "").replace("@c.us", "").replace("+", "").strip()
    payload = {"number": numero, "type": "image", "file": url_imagem}
    if legenda:
        payload["text"] = legenda
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=HEADERS)
        logger.warning("enviar_imagem status=%s body=%s", resp.status_code, resp.text[:300])


# ---------------------------------------------------------------------------
# Webhook — recebe mensagens do WhatsApp via UAZAPI
# ---------------------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    # Só processa eventos de mensagem
    event_type = body.get("EventType") or body.get("wook", "")
    if event_type not in ("messages", "RECEIVE_MESSAGE", ""):
        return JSONResponse({"status": "ignored", "event": event_type})

    msg = body.get("message", {})

    # Ignora mensagens enviadas pelo próprio bot
    if msg.get("fromMe") or msg.get("wasSentByApi") or body.get("fromMe"):
        return JSONResponse({"status": "ignored"})

    # Ignora grupos
    if msg.get("isGroup") or body.get("isGroupMsg"):
        return JSONResponse({"status": "ignored"})

    # Extrai telefone
    sender_pn = msg.get("sender_pn", "")
    telefone = (
        sender_pn.replace("@s.whatsapp.net", "").replace("@c.us", "").strip()
        or body.get("sender", "")
        or body.get("phone", "")
    )

    # Extrai texto
    texto = (
        msg.get("text")
        or msg.get("content")
        or body.get("text")
        or body.get("body")
        or body.get("content")
        or ""
    ).strip()

    if not telefone or not texto:
        return JSONResponse({"status": "ignored"})

    try:
        resposta, fotos = await asyncio.get_event_loop().run_in_executor(
            None, agent.processar_mensagem, telefone, texto
        )
    except Exception:
        logger.error("ERRO ao processar mensagem:\n%s", traceback.format_exc())
        return JSONResponse({"status": "error"})

    for url_foto in fotos:
        await enviar_imagem_url(telefone, url_foto)

    if resposta:
        await enviar_texto(telefone, resposta)

    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
def health():
    return {"status": "online", "agente": "A Amora 🍓"}
