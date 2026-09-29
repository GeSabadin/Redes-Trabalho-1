import os
import socket

HOST = "0.0.0.0"
PORTA = 5000
PASTA = "arquivos"
TAM_MAX = 65535

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock.bind((HOST, PORTA))
print(f"Servidor UDP ouvindo na porta {PORTA}...")

while True:
    try:
        dados, endereco = sock.recvfrom(TAM_MAX)
    except ConnectionResetError:
        continue

    requisicao = dados.decode("utf-8", errors="replace")
    print(f"Recebido de {endereco}: {requisicao}")

    comando, _, nome = requisicao.partition(" ")
    if comando != "GET" or not nome:
        sock.sendto(b" ERRO 999 requisicao invalida", endereco)
        continue

    #monta o caminho e breca se sair da pasta 
    caminho = os.path.abspath(os.path.join(PASTA, nome))
    if os.path.dirname(caminho) != os.path.abspath(PASTA) or not os.path.isfile(caminho):
        sock.sendto(f"ERRO 888 arquivo nao encontrado: {nome}".encode(), endereco)
        continue

    with open(caminho, "rb") as f:
        conteudo = f.read()

    try:
        sock.sendto(conteudo, endereco)
        print(f"Enviado {nome} ({len(conteudo)} bytes)")
    except OSError as e:
        # Arquivo maior que um datagrama: e isso que a Fase 4 resolve
        print(f"Nao consegui enviar {nome} ({len(conteudo)} bytes): {e}")
        sock.sendto(f"ERRO 777 arquivo grande demais para um datagrama: {nome}".encode(), endereco)