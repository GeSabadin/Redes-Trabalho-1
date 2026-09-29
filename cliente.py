import os
import socket

TAM_MAX = 65535

while True:
    entrada = input("\nServidor e arquivo (ip:porta/arquivo, ENTER para sair): ").strip()
    if not entrada:
        break

    # "127.0.0.1:5000/pequeno.txt" -> "127.0.0.1:5000" e "pequeno.txt"
    servidor, _, nome = entrada.partition("/")
    host, _, porta = servidor.rpartition(":")
    if not host or not porta.isdigit() or not nome:
        print("Formato esperado: ip:porta/arquivo")
        continue

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    sock.sendto(f"GET {nome}".encode(), (host, int(porta)))

    try:
        dados, _ = sock.recvfrom(TAM_MAX)
    except socket.timeout:
        print("O servidor nao respondeu.")
        continue
    except ConnectionResetError:
        print("Servidor fora do ar (porta fechada).")
        continue
    finally:
        sock.close()

    if dados.startswith(b"ERRO"):
        print(dados.decode())
        continue

    os.makedirs("recebidos", exist_ok=True)
    caminho = os.path.join("recebidos", os.path.basename(nome))
    with open(caminho, "wb") as f:
        f.write(dados)
    print(f"Arquivo salvo em {caminho} ({len(dados)} bytes)")
    print(dados.decode("utf-8", errors="replace"))