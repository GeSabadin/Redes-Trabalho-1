import socket

HOST = "0.0.0.0"
PORTA = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
sock.bind((HOST, PORTA))
print(f"Servidor UDP ouvindo na porta {PORTA}...")

while True:
    dados, endereco = sock.recvfrom(2048)
    print(f"Recebido de {endereco}: {dados.decode()}")
    sock.sendto(dados, endereco) 