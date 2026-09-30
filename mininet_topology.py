#!/usr/bin/env python3
"""Topologia Mininet da eleição de líder (Valentão): 5 processos + 1 servidor.

    sudo python3 mininet_topology.py            # sobe a rede e abre o CLI
    sudo python3 mininet_topology.py --demo     # roda um roteiro automático e abre o CLI
    sudo python3 mininet_topology.py --demo --no-cli
    sudo python3 mininet_topology.py --web      # + visualização em http://localhost:5001

Hosts: srv (10.0.0.1) e p1..p5 (10.0.0.2 .. 10.0.0.6), todos ligados ao switch s1
por links com atraso (LINK_DELAY).

Comandos extras no CLI do Mininet:
    crash|recover|elect pN, status pN|all   comandos de falha simulada (via servidor)
    kill pN       mata de verdade o processo pN (falha real; registra KILLED no log)
    restart pN    sobe de novo o processo pN (recuperação real)
    check         verifica se todos os ativos concordam no líder correto
    check timeline   idem, mostrando também a linha do tempo dos eventos
"""

import argparse
import os
import subprocess
import sys
import time

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.net import Mininet
from mininet.node import Controller

import check_logs
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
PROCESS_PY = os.path.join(BASE_DIR, "process.py")
SERVER_PY = os.path.join(BASE_DIR, "server.py")
COMMAND_PY = os.path.join(BASE_DIR, "command.py")


def prepare_log(path):
    """Cria/zera o log e o entrega ao usuário que chamou sudo."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as log_file:
        if os.geteuid() == 0:
            uid = int(os.environ.get("SUDO_UID", os.getuid()))
            gid = int(os.environ.get("SUDO_GID", os.getgid()))
            os.chown(directory, uid, gid)
            os.fchown(log_file.fileno(), uid, gid)
            os.fchmod(log_file.fileno(), 0o644)


def append_marker(path, process_id, event):
    """Registra no log de pN um evento que o próprio processo não consegue escrever (ex.: KILLED)."""
    with open(path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[p{process_id}] t={time.monotonic():.3f} {event}\n")


class Cluster:
    """Controla os processos rodando nos hosts (start/kill/restart), guardando os handles."""

    def __init__(self, server_host, hosts):
        self.server_host = server_host
        self.hosts = hosts  # {process_id: host}
        self.procs = {}
        self.server_proc = None

    @staticmethod
    def log_path(process_id):
        return os.path.join(LOG_DIR, f"process{process_id}.log")

    def is_running(self, process_id):
        proc = self.procs.get(process_id)
        return proc is not None and proc.poll() is None

    def start_server(self):
        log = open(os.path.join(LOG_DIR, "server.log"), "a", encoding="utf-8")
        self.server_proc = self.server_host.popen(
            ["python3", "-u", SERVER_PY], stdout=log, stderr=subprocess.STDOUT, cwd=BASE_DIR
        )
        log.close()

    def start_process(self, process_id):
        if self.is_running(process_id):
            print(f"p{process_id} já está em execução")
            return
        log = open(self.log_path(process_id), "a", encoding="utf-8")
        self.procs[process_id] = self.hosts[process_id].popen(
            ["python3", "-u", PROCESS_PY, str(process_id), config.ip_of(process_id)],
            stdout=log, stderr=subprocess.STDOUT, cwd=BASE_DIR,
        )
        log.close()

    def wait_ready(self, process_id, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with open(self.log_path(process_id), encoding="utf-8", errors="replace") as handle:
                if " RUNNING " in handle.read():
                    return True
            time.sleep(0.1)
        return False

    def start_all(self):
        prepare_log(os.path.join(LOG_DIR, "server.log"))
        for pid in self.hosts:
            prepare_log(self.log_path(pid))

        info("*** Starting server\n")
        self.start_server()

        info("*** Starting processes\n")
        for pid in self.hosts:
            info(f"*** Starting p{pid} in {config.ip_of(pid)}\n")
            self.start_process(pid)
        for pid in self.hosts:
            if not self.wait_ready(pid):
                info(f"*** ERROR: p{pid} did not start (see logs/process{pid}.log)\n")

    def kill_process(self, process_id):
        if not self.is_running(process_id):
            print(f"p{process_id} não está em execução")
            return
        self.procs[process_id].kill()
        self.procs[process_id].wait()
        append_marker(self.log_path(process_id), process_id, "KILLED")
        print(f"p{process_id} morto (kill real)")

    def send_control(self, text):
        """Envia um comando ao servidor sem bloquear o CLI (usado pela interface web)."""
        proc = self.server_host.popen(
            ["python3", COMMAND_PY, *text.split()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=BASE_DIR,
        )
        proc.wait()

    def command(self, text):
        """Envia um comando ao servidor a partir do host do próprio servidor."""
        return self.server_host.cmd(f"python3 {COMMAND_PY} {text}")

    def stop_all(self):
        for proc in list(self.procs.values()) + [self.server_proc]:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()


class BullyCLI(CLI):
    cluster = None

    @staticmethod
    def _parse_pid(line):
        text = line.strip().lower().lstrip("p")
        if text.isdigit() and 1 <= int(text) <= config.NUM_PROCESSES:
            return int(text)
        print(f"Uso: informe um processo de p1 a p{config.NUM_PROCESSES}")
        return None

    def do_kill(self, line):
        "kill pN: mata de verdade o processo pN (falha real)"
        pid = self._parse_pid(line)
        if pid:
            self.cluster.kill_process(pid)

    def do_restart(self, line):
        "restart pN: sobe de novo o processo pN (recuperação real)"
        pid = self._parse_pid(line)
        if pid:
            self.cluster.start_process(pid)

    def _control(self, action, line):
        target = line.strip().lower()
        if action == "status" and target == "all":
            self.cluster.send_control("status all")
            return
        pid = self._parse_pid(line)
        if pid:
            self.cluster.send_control(f"{action} p{pid}")

    def do_crash(self, line):
        "crash pN: falha simulada do processo pN"
        self._control("crash", line)

    def do_recover(self, line):
        "recover pN: recupera o processo pN após um crash simulado"
        self._control("recover", line)

    def do_elect(self, line):
        "elect pN: força pN a convocar uma eleição"
        self._control("elect", line)

    def do_status(self, line):
        "status <pN|all>: pede que o(s) processo(s) registrem o estado no log"
        self._control("status", line)

    def do_check(self, line):
        "check [timeline]: verifica se os processos ativos concordam no líder correto"
        check_logs.report(LOG_DIR, timeline="timeline" in line)


def build_network():
    net = Mininet(controller=Controller, link=TCLink)

    info("*** Add controller\n")
    net.addController("c0")

    info("*** Add switch\n")
    switch = net.addSwitch("s1")

    info("*** Add server\n")
    server = net.addHost("srv", ip=f"{config.SERVER_IP}/24")
    net.addLink(server, switch, delay=config.LINK_DELAY)

    info("*** Add processes\n")
    hosts = {}
    for pid in range(1, config.NUM_PROCESSES + 1):
        host = net.addHost(f"p{pid}", ip=f"{config.ip_of(pid)}/24")
        net.addLink(host, switch, delay=config.LINK_DELAY)
        hosts[pid] = host
    return net, server, hosts


def run_demo(cluster):
    """Roteiro automático: cenários sem e com falhas. O veredito vem dos logs (check_logs)."""
    settle_boot, settle_fail, settle_back = 4, 6, 4
    results = []

    def step(title, action, wait):
        print(f"\n=== {title}", flush=True)
        action()
        time.sleep(wait)
        results.append((title, check_logs.report(LOG_DIR)))

    step("1. Subida dos 5 processos, sem falhas", lambda: None, settle_boot)
    step("2. Líder p1 falha (crash simulado)", lambda: cluster.command("crash p1"), settle_fail)
    step("3. p2 (novo líder) também falha", lambda: cluster.command("crash p2"), settle_fail)
    step("4. p1 se recupera e retoma a liderança", lambda: cluster.command("recover p1"), settle_back)
    step("5. p1 é morto de verdade (kill real)", lambda: cluster.kill_process(1), settle_fail)
    step("6. Processo comum p4 falha (não deve haver nova eleição de líder)",
         lambda: cluster.command("crash p4"), settle_fail)

    def recover_everyone():
        cluster.start_process(1)
        cluster.command("recover p2")
        cluster.command("recover p4")

    step("7. p1 reinicia de verdade; p2 e p4 se recuperam", recover_everyone, settle_back + 2)

    print("\n=== RESUMO DA DEMO")
    for title, ok in results:
        print(f"  [{'OK' if ok else 'FALHOU'}] {title}")
    print("Linha do tempo completa: comando 'check timeline' no CLI, ou python3 check_logs.py --timeline")


def main():
    parser = argparse.ArgumentParser(description="Eleição de líder (Valentão) no Mininet")
    parser.add_argument("--demo", action="store_true", help="executa o roteiro automático de testes")
    parser.add_argument("--web", action="store_true", help="sobe a visualização web (Flask + React)")
    parser.add_argument("--web-port", type=int, default=5001, help="porta da visualização web (padrão 5001)")
    parser.add_argument("--no-cli", action="store_true", help="encerra após a demo, sem abrir o CLI")
    args = parser.parse_args()

    if os.geteuid() != 0:
        sys.exit("O Mininet exige root: sudo python3 mininet_topology.py")

    setLogLevel("info")
    net, server, hosts = build_network()
    net.start()
    info("*** Testing connectivity\n")
    net.pingAll()

    cluster = Cluster(server, hosts)
    try:
        cluster.start_all()
        info("\n*** Network ready!!\n")
        info("*** Exemplos: crash p1 | recover p1 | elect p4 | status all | kill p1 | restart p1 | check\n\n")

        if args.web:
            import web_server
            web_server.start_in_thread(LOG_DIR, cluster, args.web_port)
            info(f"*** Visualização web: http://localhost:{args.web_port}\n")

        if args.demo:
            run_demo(cluster)
        if not args.no_cli:
            BullyCLI.cluster = cluster
            BullyCLI(net)
    finally:
        info("*** Finishing processes\n")
        cluster.stop_all()
        net.stop()


if __name__ == "__main__":
    main()
