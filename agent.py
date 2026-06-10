import json
from pathlib import Path
import anthropic

import config
from services import session_service, sheets_service, media_service
from services.session_service import Estado, Sessao
from services.order_service import Carrinho

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
_system_prompt = Path("prompts/system_prompt.txt").read_text(encoding="utf-8")

MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Definição das ferramentas (function calling)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "get_pratos_do_dia",
        "description": "Retorna os pratos disponíveis hoje (nome, descrição, preços e ID da foto).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_descricao_prato",
        "description": "Retorna a descrição detalhada de um prato específico pelo nome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_prato": {"type": "string", "description": "Nome do prato a consultar"}
            },
            "required": ["nome_prato"],
        },
    },
    {
        "name": "adicionar_item",
        "description": "Adiciona um item ao carrinho do cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_prato": {"type": "string"},
                "tipo":       {"type": "string", "enum": ["pf", "marmita"], "description": "'pf' para Prato Feito, 'marmita' para Marmita"},
            },
            "required": ["nome_prato", "tipo"],
        },
    },
    {
        "name": "remover_item",
        "description": "Remove um item do carrinho do cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_prato": {"type": "string"},
                "tipo":       {"type": "string", "enum": ["pf", "marmita"]},
            },
            "required": ["nome_prato", "tipo"],
        },
    },
    {
        "name": "ver_carrinho",
        "description": "Retorna o resumo atual do carrinho com total.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "registrar_pagamento",
        "description": "Registra a forma de pagamento escolhida e finaliza o pedido.",
        "input_schema": {
            "type": "object",
            "properties": {
                "forma": {
                    "type": "string",
                    "enum": ["Dinheiro", "Cartão de Débito", "Cartão de Crédito", "PIX"],
                }
            },
            "required": ["forma"],
        },
    },
]


# ---------------------------------------------------------------------------
# Execução das ferramentas
# ---------------------------------------------------------------------------
def _executar_tool(name: str, inputs: dict, sessao: Sessao) -> str:
    if name == "get_pratos_do_dia":
        pratos = sheets_service.get_pratos_do_dia()
        if not pratos:
            return "Não há pratos cadastrados para hoje."
        resultado = []
        for p in pratos:
            foto_url = media_service.get_foto_url(p["foto_id"]) or "sem foto"
            resultado.append(
                f"Prato {p['prato_numero']}: {p['nome_prato']}\n"
                f"  PF: R$ {p['preco_pf']:.2f} | Marmita: R$ {p['preco_marmita']:.2f}\n"
                f"  Foto: {foto_url}"
            )
        return "\n\n".join(resultado)

    if name == "get_descricao_prato":
        prato = sheets_service.get_prato_por_nome(inputs["nome_prato"])
        if not prato:
            return f"Não encontrei o prato '{inputs['nome_prato']}' na planilha."
        return (
            f"{prato['nome_prato']}: {prato['descricao']}\n"
            f"PF: R$ {prato['preco_pf']:.2f} | Marmita: R$ {prato['preco_marmita']:.2f}"
        )

    if name == "adicionar_item":
        nome = inputs["nome_prato"]
        tipo = inputs["tipo"]
        prato = sheets_service.get_prato_por_nome(nome)
        if not prato:
            return f"Prato '{nome}' não encontrado na planilha."
        preco = prato["preco_pf"] if tipo == "pf" else prato["preco_marmita"]
        sessao.carrinho.adicionar(prato["nome_prato"], tipo, preco)
        sessao.atualizar_estado(Estado.PEDINDO)
        return f"✅ Adicionado: {prato['nome_prato']} ({'Prato Feito' if tipo == 'pf' else 'Marmita'}) — R$ {preco:.2f}"

    if name == "remover_item":
        sessao.carrinho.remover(inputs["nome_prato"], inputs["tipo"])
        return f"Item removido do carrinho."

    if name == "ver_carrinho":
        return sessao.carrinho.resumo_texto()

    if name == "registrar_pagamento":
        sessao.carrinho.forma_pagamento = inputs["forma"]
        sessao.atualizar_estado(Estado.CONCLUIDO)
        return f"Forma de pagamento registrada: {inputs['forma']}. Pedido finalizado!"

    return "Ferramenta desconhecida."


# ---------------------------------------------------------------------------
# Loop principal do agente
# ---------------------------------------------------------------------------
def processar_mensagem(telefone: str, mensagem_usuario: str) -> tuple[str, list[str]]:
    """
    Processa uma mensagem do usuário e retorna (texto_resposta, lista_urls_fotos).
    """
    sessao = session_service.get_ou_criar(telefone)
    sessao.adicionar_mensagem("user", mensagem_usuario)

    fotos_para_enviar: list[tuple[str, str]] = []  # (url, legenda)

    # Primeira mensagem: injeta contexto e coleta fotos
    if sessao.estado == Estado.INICIO:
        pratos = sheets_service.get_pratos_do_dia()
        for p in pratos:
            url = media_service.get_foto_url(p["foto_id"])
            if url:
                legenda = f"{p['nome_prato']}\nPF: R$ {p['preco_pf']:.2f} | Marmita: R$ {p['preco_marmita']:.2f}"
                fotos_para_enviar.append((url, legenda))

        # Injeta instrução explícita para o Claude se apresentar e listar o cardápio
        pratos_texto = "\n".join(
            f"- {p['nome_prato']}: PF R$ {p['preco_pf']:.2f} / Marmita R$ {p['preco_marmita']:.2f}"
            for p in pratos
        ) if pratos else "Nenhum prato cadastrado para hoje."

        sessao.historico.insert(0, {
            "role": "user",
            "content": (
                f"[SISTEMA] Esta é a primeira mensagem do cliente. "
                f"Apresente-se como A Amora e informe os pratos de hoje:\n{pratos_texto}\n"
                f"As fotos já foram enviadas automaticamente. Não mencione links ou fotos no texto."
            ),
        })
        sessao.historico.insert(1, {
            "role": "assistant",
            "content": "Entendido! Vou me apresentar e mostrar os pratos do dia.",
        })
        sessao.atualizar_estado(Estado.CARDAPIO)

    # Chama o Claude com o histórico completo
    resposta_texto = _chamar_claude(sessao)
    sessao.adicionar_mensagem("assistant", resposta_texto)

    return resposta_texto, fotos_para_enviar


def _chamar_claude(sessao: Sessao) -> str:
    """Executa o loop de chamada ao Claude, incluindo resolução de tool calls."""
    messages = list(sessao.historico)

    while True:
        response = _client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        # Sem tool call → retorna texto direto
        if response.stop_reason == "end_turn":
            return _extrair_texto(response)

        # Com tool call → executa as ferramentas e continua o loop
        if response.stop_reason == "tool_use":
            tool_results = []
            messages.append({"role": "assistant", "content": response.content})

            for block in response.content:
                if block.type == "tool_use":
                    resultado = _executar_tool(block.name, block.input, sessao)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": resultado,
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Qualquer outro stop_reason
        return _extrair_texto(response)


def _extrair_texto(response) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""
