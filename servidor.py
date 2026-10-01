import argparse
import hashlib
import os
import random
import socket
import threading
import time

from protocolo import DADOS, ERRO, FIM, META, META_CARGA, TAM_MAX, TAM_PEDACO, montar_pacote

HOST = "0.0.0.0"
PASTA = "arquivos"

# Opcoes de linha de comando: python servidor.py --porta 5000 --perda 0.01
parser = argparse.ArgumentParser(description="Servidor UDP de arquivos")
parser.add_argument("--porta", type=int, default=5000)
parser.add_argument("--perda", type=float, default=0.0,
                    help="chance (0 a 1) de descartar cada pedaco, para simular perda")
args = parser.parse_args()
PORTA = args.porta
PERDA = args.perda

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORTA))
sock.settimeout(0.5)   # o recvfrom acorda a cada 0,5 s, para o Ctrl+C funcionar no Windows

print(f"Servidor UDP ouvindo na porta {PORTA}...")
try:
    for ip in sorted({info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}):
        print(f"  clientes podem usar: {ip}:{PORTA}/<arquivo>")
except socket.gaierror:
    pass
if PERDA:
    print(f"  [simulacao] descartando {PERDA:.1%} dos pedacos")


def enviar_erro(nome_erro, detalhe, endereco):
    carga = f"{nome_erro} {detalhe}".encode()
    sock.sendto(montar_pacote(ERRO, 0, 0, carga), endereco)


def enviar_pedacos(conteudo, total, seqs, endereco):
    """Envia os pedacos da lista 'seqs' e depois o FIM. Devolve quantos foram descartados."""
    descartados = 0
    for i, seq in enumerate(seqs):
        if PERDA and random.random() < PERDA:
            descartados += 1              # simula a perda: simplesmente nao envia
            continue
        pedaco = conteudo[seq * TAM_PEDACO:(seq + 1) * TAM_PEDACO]
        sock.sendto(montar_pacote(DADOS, seq, total, pedaco), endereco)
        if i % 64 == 63:
            time.sleep(0.001)
    sock.sendto(montar_pacote(FIM, 0, total), endereco)
    return descartados


def atender(dados, endereco):
    """Atende UMA requisicao. Roda numa thread propria, por isso varios clientes sao atendidos juntos."""
    requisicao = dados.decode("utf-8", errors="replace")
    print(f"[{endereco[0]}:{endereco[1]}] {requisicao[:70]}{' ...' if len(requisicao) > 70 else ''}")

    # "GET nome"               -> nome, seqs = None (arquivo inteiro)
    # "RESEND nome 3,10,11"    -> nome, seqs = [3, 10, 11]
    comando, _, nome = requisicao.partition(" ")
    seqs = None
    if comando == "RESEND":
        nome, _, lista = nome.rpartition(" ")
        try:
            seqs = [int(s) for s in lista.split(",")]
        except ValueError:
            nome = ""
    elif comando != "GET":
        nome = ""
    if not nome:
        enviar_erro("REQUISICAO_INVALIDA", requisicao[:50], endereco)
        return

    caminho = os.path.abspath(os.path.join(PASTA, nome))
    if os.path.dirname(caminho) != os.path.abspath(PASTA) or not os.path.isfile(caminho):
        enviar_erro("ARQUIVO_INEXISTENTE", nome, endereco)
        return

    with open(caminho, "rb") as f:
        conteudo = f.read()

    tamanho = len(conteudo)
    total = -(-tamanho // TAM_PEDACO)

    if seqs is None:
        # GET: manda o META e depois o arquivo inteiro
        sha = hashlib.sha256(conteudo).digest()
        sock.sendto(montar_pacote(META, 0, total, META_CARGA.pack(tamanho, TAM_PEDACO, sha)), endereco)
        seqs = range(total)
    else:
        # RESEND: so os pedacos pedidos (ignorando numeros que nao existem)
        seqs = [s for s in seqs if 0 <= s < total]

    descartados = enviar_pedacos(conteudo, total, seqs, endereco)
    aviso = f" ({descartados} descartados de proposito)" if descartados else ""
    print(f"[{endereco[0]}:{endereco[1]}] enviados {len(seqs) - descartados} de {len(seqs)} pedacos de {nome}{aviso}")


try:
    while True:
        try:
            dados, endereco = sock.recvfrom(TAM_MAX)
        except socket.timeout:
            continue                       # ninguem mandou nada; volta a esperar
        except ConnectionResetError:
            continue                       # Windows: cliente que ja fechou
        threading.Thread(target=atender, args=(dados, endereco), daemon=True).start()
except KeyboardInterrupt:
    print("\nServidor encerrado.")
finally:
    sock.close()
