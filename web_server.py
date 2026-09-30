#!/usr/bin/env python3
"""Backend Flask da visualização em tempo real.

Lê os logs dos processos (logs/process*.log), reconstrói o estado de cada nó e
serve a interface React (web/index.html). Opcionalmente envia comandos ao
cluster Mininet (crash / recover / elect / kill / restart).

Modos de uso:
    sudo python3 mininet_topology.py --web          # integrado ao Mininet (com botões)
    python3 web_server.py                           # somente leitura dos logs (sem botões)

API:
    GET  /api/state?since=<seq>   estado dos nós + eventos novos desde <seq>
    POST /api/command             {"action": "crash|recover|elect|kill|restart", "target": "p1"}
"""

import logging
import os
import re
import threading

from flask import Flask, jsonify, request, send_from_directory

import check_logs
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
DEFAULT_PORT = 5001
MAX_EVENTS = 5000  # memória: mantém só os mais recentes

ACTIONS = {"crash", "recover", "elect", "kill", "restart"}


def _new_node(pid: int) -> dict:
    return {
        "id": pid, "name": f"p{pid}", "alive": False, "status": "OFF",
        "leader": None, "view": [], "last_heartbeat": 0, "down_kind": None,
        "os_pid": None,
    }


class LogState:
    """Acompanha (tail) os logs e mantém o estado derivado dos eventos."""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.offsets: dict[str, int] = {}
        self.events: list[dict] = []
        self.seq = 0
        self.nodes = {pid: _new_node(pid) for pid in range(1, config.NUM_PROCESSES + 1)}

    # ---------------------------------------------------------------- leitura
    def _read_new_lines(self) -> list[str]:
        lines = []
        for path in sorted(os.path.join(self.log_dir, f) for f in os.listdir(self.log_dir)
                           if re.fullmatch(r"process\d+\.log", f)) if os.path.isdir(self.log_dir) else []:
            size = os.path.getsize(path)
            offset = self.offsets.get(path, 0)
            if size < offset:  # log foi zerado (nova execução): recomeça tudo
                self._reset()
                return self._read_new_lines()
            if size == offset:
                continue
            with open(path, "rb") as handle:
                handle.seek(offset)
                chunk = handle.read()
            end = chunk.rfind(b"\n")
            if end < 0:  # linha ainda incompleta
                continue
            self.offsets[path] = offset + end + 1
            lines.extend(chunk[: end + 1].decode("utf-8", errors="replace").splitlines())
        return lines

    def poll(self):
        with self.lock:
            batch = []
            for line in self._read_new_lines():
                parsed = check_logs.parse_line(line)
                if parsed:
                    pid, t, event, fields = parsed
                    batch.append((t, pid, event, fields))
            batch.sort(key=lambda row: row[0])  # t é monotonic, comparável entre processos
            for t, pid, event, fields in batch:
                self.seq += 1
                ev = {"seq": self.seq, "t": t, "pid": pid, "event": event, "fields": fields}
                self.events.append(ev)
                self._apply(ev)
            if len(self.events) > MAX_EVENTS:
                del self.events[: len(self.events) - MAX_EVENTS]

    # ------------------------------------------------- estado derivado (por evento)
    def _apply(self, ev: dict):
        node = self.nodes.get(ev["pid"])
        if node is None:
            return
        event, f = ev["event"], ev["fields"]
        if event == "RUNNING":
            if f.get("os_pid"):
                node["os_pid"] = f.get("os_pid")
        elif event in ("START", "RECOVER"):
            node.update(alive=True, status="NORMAL", leader=None, view=[], down_kind=None)
        elif event in ("CRASH", "KILLED"):
            node.update(alive=False, status="DEAD", leader=None, view=[],
                        down_kind="crash" if event == "CRASH" else "killed",
                        os_pid=node["os_pid"] if event == "CRASH" else None)
        elif not node["alive"]:
            return
        elif event == "HEARTBEAT_SENT":
            node["last_heartbeat"] = ev["seq"]
        elif event == "ELECTION_START":
            node["status"] = "ELECTING"
        elif event == "WAIT_COORDINATOR":
            node["status"] = "WAIT_COORD"
        elif event in ("ELECTION_TIMEOUT", "COORDINATOR_TIMEOUT"):
            node["status"] = "NORMAL"  # ELECTION_START / LEADER logo em seguida refinam
        elif event == "SEND_COORDINATOR":
            node["status"] = "NORMAL"  # só é enviado por quem acabou de assumir a liderança
            node["leader"] = node["name"]
        elif event == "LEADER":
            leader = f.get("leader")
            node["leader"] = None if leader in (None, "none") else leader
            node["status"] = "NORMAL"
        elif event == "RECV_COORDINATOR":
            sender = f.get("from", "")
            if sender[1:].isdigit() and int(sender[1:]) < ev["pid"]:
                node["status"] = "NORMAL"  # anúncio de ID menor é aceito
        elif event == "PEER_UP":
            peer = f.get("peer")
            if peer and peer not in node["view"]:
                node["view"].append(peer)
        elif event == "PEER_DOWN":
            peer = f.get("peer")
            if peer in node["view"]:
                node["view"].remove(peer)

    # ------------------------------------------------------------------- saída
    def snapshot(self, since: int) -> dict:
        self.poll()
        with self.lock:
            nodes = [dict(n, view=sorted(n["view"])) for n in self.nodes.values()]
            alive = [n for n in nodes if n["alive"]]
            expected = f"p{min(n['id'] for n in alive)}" if alive else None
            converged = bool(alive) and all(n["leader"] == expected for n in alive)
            if since > self.seq:  # cliente com estado de uma execução anterior
                since = 0
            new = [e for e in self.events if e["seq"] > since]
            return {
                "seq": self.seq,
                "reset": since == 0,
                "nodes": nodes,
                "expected_leader": expected,
                "converged": converged,
                "events": new[-500:],
                "heartbeat_interval": config.HEARTBEAT_INTERVAL,
                "controllable": False,
            }


def create_app(log_dir: str, cluster=None) -> Flask:
    app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
    state = LogState(log_dir)
    cluster_lock = threading.Lock()

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/api/state")
    def api_state():
        since = request.args.get("since", default=0, type=int)
        data = state.snapshot(since)
        data["controllable"] = cluster is not None
        return jsonify(data)

    @app.post("/api/command")
    def api_command():
        if cluster is None:
            return jsonify(ok=False, error="Modo somente leitura: suba pelo mininet_topology.py --web"), 503
        body = request.get_json(silent=True) or {}
        action, target = str(body.get("action", "")), str(body.get("target", ""))
        match = re.fullmatch(r"p([1-9]\d*)", target)
        if action not in ACTIONS or not match or int(match.group(1)) > config.NUM_PROCESSES:
            return jsonify(ok=False, error="comando inválido"), 400
        pid = int(match.group(1))
        with cluster_lock:
            if action == "kill":
                cluster.kill_process(pid)
            elif action == "restart":
                cluster.start_process(pid)
            else:
                cluster.send_control(f"{action} {target}")
        return jsonify(ok=True)

    return app


def start_in_thread(log_dir: str, cluster=None, port: int = DEFAULT_PORT):
    """Sobe o Flask em uma thread daemon (usado pela topologia Mininet)."""
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # não poluir o CLI do Mininet
    app = create_app(log_dir, cluster)
    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False),
        daemon=True,
    )
    thread.start()
    return thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visualização web (somente leitura dos logs)")
    parser.add_argument("--logs", default=os.path.join(BASE_DIR, "logs"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    print(f"Abra http://localhost:{args.port}")
    create_app(args.logs).run(host="127.0.0.1", port=args.port, threaded=True)