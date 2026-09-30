"""Servidor injetor: recebe comandos no canal de controle (127.0.0.1:9000)
e os encaminha por UDP aos processos como Trigger.

O servidor NÃO participa do algoritmo: só provoca falhas/recuperações e consultas.

Comandos:
    crash <pN>      falha simulada do processo pN
    recover <pN>    recuperação do processo pN
    elect <pN>      força pN a convocar uma eleição
    status <pN|all> pede que o(s) processo(s) registrem seu estado no log
"""

import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from messages import Trigger, serialize

COMMANDS = {"crash": "CRASH", "recover": "RECOVER", "elect": "ELECT", "status": "STATUS"}
USAGE = "crash <p> | recover <p> | elect <p> | status <p|all>"


def main():
    peers = config.peers()

    net_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    net_socket.bind((config.SERVER_IP, config.SERVER_PORT))

    control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    control.bind((config.CONTROL_IP, config.CONTROL_PORT))

    print(f"[SERVER] UDP socket on {config.SERVER_IP}:{config.SERVER_PORT}", flush=True)
    print(f"[CONTROLLER] listening on {config.CONTROL_IP}:{config.CONTROL_PORT}", flush=True)
    print(f"Commands: {USAGE}", flush=True)

    while True:
        data, _addr = control.recvfrom(4096)
        text = data.decode("utf-8", errors="replace").strip()
        print(f"[CONTROLLER] command received: {text}", flush=True)

        parts = text.split()
        if len(parts) != 2 or parts[0] not in COMMANDS:
            print(f"Command NOT FOUND or malformed: {text!r}. Use: {USAGE}", flush=True)
            continue

        action, target = COMMANDS[parts[0]], parts[1]
        # O CLI do Mininet troca nomes de host (p1) pelo IP; aceita os dois.
        target = {ip: name for name, (ip, _port) in peers.items()}.get(target, target)
        if target == "all" and action == "STATUS":
            targets = list(peers)
        elif target in peers:
            targets = [target]
        else:
            print(f"Routing Error: process '{target}' not found!", flush=True)
            continue

        for name in targets:
            net_socket.sendto(serialize(Trigger(action=action)), peers[name])
            print(f"[SEND] {name} {peers[name]} - {action}", flush=True)


if __name__ == "__main__":
    main()
