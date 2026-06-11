from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ItemPedido:
    nome: str
    tipo: str        # "pf" ou "marmita"
    preco: float
    quantidade: int = 1
    ajustes: list[str] = field(default_factory=list)  # ex: ["sem cebola", "extra queijo"]

    @property
    def subtotal(self) -> float:
        return self.preco * self.quantidade


@dataclass
class Carrinho:
    itens: list[ItemPedido] = field(default_factory=list)
    forma_pagamento: Optional[str] = None

    def adicionar(self, nome: str, tipo: str, preco: float, ajustes: list[str] | None = None):
        ajustes = ajustes or []
        # Se o mesmo item já está no carrinho (sem ajustes), incrementa quantidade
        for item in self.itens:
            if item.nome.lower() == nome.lower() and item.tipo == tipo and not ajustes and not item.ajustes:
                item.quantidade += 1
                return
        self.itens.append(ItemPedido(nome=nome, tipo=tipo, preco=preco, ajustes=ajustes))

    def remover(self, nome: str, tipo: str):
        self.itens = [
            i for i in self.itens
            if not (i.nome.lower() == nome.lower() and i.tipo == tipo)
        ]

    def total(self) -> float:
        return round(sum(i.subtotal for i in self.itens), 2)

    def resumo_texto(self) -> str:
        if not self.itens:
            return "Nenhum item no pedido ainda."
        linhas = ["📋 *Resumo do seu pedido:*\n"]
        for item in self.itens:
            tipo_label = "Prato Feito" if item.tipo == "pf" else "Marmita"
            linhas.append(
                f"• {item.quantidade}x {item.nome} ({tipo_label}) — R$ {item.subtotal:.2f}"
            )
            for ajuste in item.ajustes:
                linhas.append(f"  ↳ {ajuste}")
        linhas.append(f"\n💰 *Total: R$ {self.total():.2f}*")
        return "\n".join(linhas)

    def esta_vazio(self) -> bool:
        return len(self.itens) == 0
