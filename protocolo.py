import struct
import zlib

TAM_PEDACO = 1400  
TAM_MAX = 65535     

CABECALHO = struct.Struct("!BIIHI")

# Tipos de pacote
META, DADOS, ERRO, FIM = 1, 2, 3, 4

META_CARGA = struct.Struct("!QH32s")


def montar_pacote(tipo, seq, total, carga=b""):
    crc = zlib.crc32(carga)
    return CABECALHO.pack(tipo, seq, total, len(carga), crc) + carga


def abrir_pacote(datagrama):
    #Devolve (tipo, seq, total, carga), ou None se o pacote estiver corrompido.
    if len(datagrama) < CABECALHO.size:
        return None
    tipo, seq, total, tamanho, crc = CABECALHO.unpack_from(datagrama)
    carga = datagrama[CABECALHO.size:]
    if len(carga) != tamanho or zlib.crc32(carga) != crc:
        return None
    return tipo, seq, total, carga