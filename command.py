"""Envia comandos ao servidor pelo canal de controle (127.0.0.1:9000).

Uso (dentro do host do servidor no Mininet):
    srv sh -c "python3 command.py crash p1"     # aspas evitam a troca de p1 pelo IP no CLI
    srv sh -c "python3 command.py status all"
    srv python3 command.py                      # modo interativo

No CLI da topologia prefira os comandos diretos: crash p1, recover p1, elect p4, status all.
"""

import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config


def send(text: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(text.encode("utf-8"), (config.CONTROL_IP, config.CONTROL_PORT))
    sock.close()


def main():
    if len(sys.argv) > 1:
        send(" ".join(sys.argv[1:]))
        return

    print("Comandos: crash <p> | recover <p> | elect <p> | status <p|all> | exit")
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if text in ("exit", "quit"):
            break
        if text:
            send(text)


if __name__ == "__main__":
    main()
