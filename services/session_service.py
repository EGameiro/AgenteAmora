from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time

from services.order_service import Carrinho


class Estado(str, Enum):
    INICIO      = "inicio"
    CARDAPIO    = "cardapio"
    PEDINDO     = "pedindo"
    UPSELL      = "upsell"
    FECHAMENTO  = "fechamento"
    CONCLUIDO   = "concluido"


@dataclass
class Sessao:
    telefone: str
    estado: Estado = Estado.INICIO
    carrinho: Carrinho = field(default_factory=Carrinho)
    historico: list[dict] = field(default_factory=list)   # mensagens p/ o Claude
    criado_em: float = field(default_factory=time.time)
    atualizado_em: float = field(default_factory=time.time)

    def adicionar_mensagem(self, role: str, content: str):
        self.historico.append({"role": role, "content": content})
        self.atualizado_em = time.time()

    def atualizar_estado(self, novo_estado: Estado):
        self.estado = novo_estado
        self.atualizado_em = time.time()


# Armazenamento em memória: telefone → Sessao
_sessoes: dict[str, Sessao] = {}

SESSION_TTL = 3600 * 4  # 4 horas sem atividade expira a sessão


def get_ou_criar(telefone: str) -> Sessao:
    _limpar_expiradas()
    if telefone not in _sessoes:
        _sessoes[telefone] = Sessao(telefone=telefone)
    return _sessoes[telefone]


def get(telefone: str) -> Optional[Sessao]:
    return _sessoes.get(telefone)


def encerrar(telefone: str):
    _sessoes.pop(telefone, None)


def _limpar_expiradas():
    agora = time.time()
    expirados = [t for t, s in _sessoes.items() if agora - s.atualizado_em > SESSION_TTL]
    for t in expirados:
        del _sessoes[t]
