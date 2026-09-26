import socket

terminal_local = 1

if terminal_local:
    SERVIDOR = ("127.0.0.1", 5000)
else:
    SERVIDOR = ("192.168.0.83", 5000)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3) 

sock.sendto("AUEPA".encode(), SERVIDOR)
try:
    dados, _ = sock.recvfrom(2048)
    print("Resposta do servidor:", dados.decode())
except socket.timeout:
    print("O servidor não respondeu.")