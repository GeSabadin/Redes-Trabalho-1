import hashlib
import os
import socket
import sys
import time

from protocolo import DADOS, ERRO, FIM, META, META_CARGA, TAM_MAX, abrir_pacote

TIMEOUT = 1               # segundos sem receber nada = fim da rajada
MAX_TENTATIVAS = 15       # rodadas seguidas sem nada novo antes de desistir
MAX_POR_REENVIO = 200     # quantos numeros cabem em um RESEND


def ler_lista_pedacos(texto):
    """'3, 10-12' -> {3, 10, 11, 12}. Texto vazio -> conjunto vazio."""
    seqs = set()
    for parte in texto.replace(" ", "").split(","):
        if not parte:
            continue
        inicio, traco, fim = parte.partition("-")
        if not inicio.isdigit() or (traco and not fim.isdigit()):
            raise ValueError(f"trecho invalido: {parte}")
        fim = int(fim) if traco else int(inicio)
        seqs.update(range(int(inicio), fim + 1))
    return seqs


def receber_rajada(sock, pedacos, descartar):
    """Recebe ate chegar FIM, ERRO ou passar TIMEOUT sem nada.
    Guarda os pedacos em 'pedacos'. Devolve (meta, erro, novos)."""
    meta = erro = None
    novos = descartados = corrompidos = 0
    while True:
        try:
            datagrama, _ = sock.recvfrom(TAM_MAX)
        except socket.timeout:
            break
        except ConnectionResetError:
            # Windows: servidor fora do ar. O erro chega na hora, entao
            # esperamos o timeout para nao gastar as tentativas de uma vez.
            time.sleep(TIMEOUT)
            break

        pacote = abrir_pacote(datagrama)
        if pacote is None:
            corrompidos += 1
            continue
        tipo, seq, total, carga = pacote

        if tipo == ERRO:
            erro = carga.decode()
            break
        elif tipo == META:
            tamanho, _, sha = META_CARGA.unpack(carga)
            meta = (tamanho, sha, total)
        elif tipo == DADOS and seq not in pedacos:
            if seq in descartar:
                descartar.discard(seq)        # descarta so na primeira vez
                descartados += 1
                continue
            pedacos[seq] = carga
            novos += 1
        elif tipo == FIM:
            break

    if descartados:
        print(f"  [simulacao] {descartados} pedacos descartados de proposito")
    if corrompidos:
        print(f"  {corrompidos} pacotes descartados por checksum invalido")
    return meta, erro, novos


def baixar(host, porta, nome, descartar):
    """Baixa o arquivo, pedindo de novo o que faltar. Devolve os bytes ou None."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    sock.settimeout(TIMEOUT)

    pedacos = {}          # seq -> bytes do pedaco
    meta = None           # (tamanho, sha256, total)
    tentativas = 0
    pedido = f"GET {nome}"

    try:
        while True:
            print(f"Enviando: {pedido[:70]}{' ...' if len(pedido) > 70 else ''}")
            sock.sendto(pedido.encode(), (host, porta))
            meta_rodada, erro, novos = receber_rajada(sock, pedacos, descartar)

            if erro:
                print(f"ERRO {erro}")
                return None
            if meta_rodada:
                meta = meta_rodada
                print(f"{nome}: {meta[0]} bytes em {meta[2]} pedacos")

            if meta_rodada or novos:
                tentativas = 0
            else:
                tentativas += 1
                if tentativas == MAX_TENTATIVAS:
                    print(f"O servidor nao respondeu apos {MAX_TENTATIVAS} tentativas.")
                    return None
                print(f"  sem resposta, tentando de novo ({tentativas}/{MAX_TENTATIVAS})")

            if meta is None:
                pedido = f"GET {nome}"        # nem o META chegou: pede tudo de novo
                continue

            tamanho, sha, total = meta
            faltando = [s for s in range(total) if s not in pedacos]
            if not faltando:
                break

            lote = faltando[:MAX_POR_REENVIO]
            print(f"  faltam {len(faltando)} pedacos, pedindo reenvio de {len(lote)}")
            pedido = f"RESEND {nome} " + ",".join(str(s) for s in lote)
    finally:
        sock.close()

    dados = b"".join(pedacos[s] for s in range(total))
    if hashlib.sha256(dados).digest() != sha:
        print("ERRO: o SHA-256 do arquivo montado nao confere com o do servidor")
        return None
    return dados


def executar(entrada, descartar_txt):
    """Valida o endereco digitado, baixa o arquivo e salva em recebidos/."""
    servidor, _, nome = entrada.partition("/")
    host, _, porta = servidor.rpartition(":")
    if not host or not porta.isdigit() or not nome:
        print("Formato esperado: ip:porta/arquivo")
        return
    try:
        descartar = ler_lista_pedacos(descartar_txt)
    except ValueError as e:
        print(f"Lista invalida: {e}")
        return

    inicio = time.time()
    dados = baixar(host, int(porta), nome, descartar)
    if dados is None:
        return
    duracao = time.time() - inicio

    os.makedirs("recebidos", exist_ok=True)
    caminho = os.path.join("recebidos", os.path.basename(nome))
    with open(caminho, "wb") as f:
        f.write(dados)
    print(f"Arquivo OK, SHA-256 confere. Salvo em {caminho} ({len(dados)} bytes em {duracao:.1f} s)")
    if nome.endswith(".txt"):
        print(dados.decode("utf-8", errors="replace")[:300])


# Modo direto:     python cliente.py 127.0.0.1:5000/grande.bin [3,10-12]
# Modo interativo: python cliente.py
if len(sys.argv) > 1:
    executar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
else:
    while True:
        entrada = input("\nServidor e arquivo (ip:porta/arquivo, ENTER para sair): ").strip()
        if not entrada:
            break
        descartar_txt = input("Pedacos para descartar (ex: 3,10-12; ENTER = nenhum): ")
        executar(entrada, descartar_txt)
