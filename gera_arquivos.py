import os

os.makedirs("arquivos", exist_ok=True)
os.makedirs("recebidos", exist_ok=True)

# Arquivo grande: 15 MB de bytes aleatórios
with open("arquivos/grande.bin", "wb") as f:
    f.write(os.urandom(15 * 1024 * 1024))

# Arquivo verificavel visualmente
with open("arquivos/pequeno.txt", "w", encoding="utf-8") as f:
    f.write("Olá! Este é um arquivo de teste do trabalho de UDP.\n" * 100)

print("Arquivos de teste criados.")