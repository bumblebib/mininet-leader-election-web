"""Processo do sistema distribuído: socket UDP + BullyNode.

Uso: python3 process.py <process_id> <ip>
"""

import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from bully import BullyNode
from messages import deserialize, serialize


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 process.py <process_id> <ip>")
        sys.exit(1)

    process_id = int(sys.argv[1])
    ip = sys.argv[2]
    if not 1 <= process_id <= config.NUM_PROCESSES:
        print(f"process_id deve estar entre 1 e {config.NUM_PROCESSES}")
        sys.exit(1)

    peers = config.peers()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, config.PORT))

    def send(packet, dest):
        try:
            sock.sendto(serialize(packet), peers[dest])
        except OSError:
            pass  # destino inalcançável: para o algoritmo equivale a um processo falho

    node = BullyNode(process_id, config.NUM_PROCESSES, send=send, now=time.monotonic, log_heartbeats=True)
    node.log("RUNNING", f"addr={ip}:{config.PORT} os_pid={os.getpid()}")
    node.start()

    def ticker():
        while True:
            node.tick()
            time.sleep(config.TICK_INTERVAL)

    threading.Thread(target=ticker, daemon=True).start()

    while True:
        try:
            data, _source = sock.recvfrom(65535)
        except OSError:
            continue
        try:
            packet = deserialize(data)
        except (ValueError, KeyError, TypeError):
            continue
        node.handle(packet)


if __name__ == "__main__":
    main()