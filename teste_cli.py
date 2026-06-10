"""
Teste local via terminal — simula uma conversa sem precisar do WhatsApp.
Uso: python teste_cli.py
"""
import agent

TELEFONE_TESTE = "5511999999999"

print("=" * 50)
print("  Agente A Amora — Teste CLI")
print("  Digite 'sair' para encerrar")
print("=" * 50)
print()

# Simula primeira mensagem para disparar apresentação
resposta, fotos = agent.processar_mensagem(TELEFONE_TESTE, "Olá")
if fotos:
    print(f"[FOTOS QUE SERIAM ENVIADAS: {fotos}]")
print(f"A Amora: {resposta}\n")

while True:
    entrada = input("Você: ").strip()
    if entrada.lower() == "sair":
        break
    if not entrada:
        continue

    resposta, fotos = agent.processar_mensagem(TELEFONE_TESTE, entrada)
    if fotos:
        print(f"[FOTOS: {fotos}]")
    print(f"A Amora: {resposta}\n")
