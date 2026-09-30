#!/usr/bin/env python3
"""Verifica se o sistema convergiu para o líder correto a partir dos logs.

Invariante: todo processo ATIVO termina com líder = menor ID entre os ativos.

Um processo é considerado ativo se o último evento de ciclo de vida dele foi
START ou RECOVER, e falho se foi CRASH (falha simulada) ou KILLED (kill real,
registrado pela topologia).

Uso:
    python3 check_logs.py                 # resumo + veredito
    python3 check_logs.py --timeline      # também imprime a linha do tempo
    python3 check_logs.py --logs outra_pasta
"""

import argparse
import glob
import os
import re
import sys
import time

LINE_RE = re.compile(r"^\[p(\d+)\] t=([0-9]+(?:\.[0-9]+)?) ([A-Z_]+)(?: (.*))?$")

ALIVE_EVENTS = {"START", "RECOVER"}
DEAD_EVENTS = {"CRASH", "KILLED"}
TIMELINE_EVENTS = {
    "START", "RECOVER", "CRASH", "KILLED",
    "PEER_UP", "PEER_DOWN",
    "ELECTION_START", "ELECTION_TIMEOUT", "COORDINATOR_TIMEOUT",
    "COORDINATOR_REJECTED", "LEADER",
}


def parse_line(line: str):
    """Retorna (pid, t, evento, campos) ou None se a linha não for de evento."""
    match = LINE_RE.match(line.strip())
    if not match:
        return None
    fields = {}
    for token in (match.group(4) or "").split():
        if "=" in token:
            key, value = token.split("=", 1)
            fields[key] = value
    return int(match.group(1)), float(match.group(2)), match.group(3), fields


def parse_all(lines_by_pid: dict[int, list[str]]) -> dict[int, list[tuple]]:
    events: dict[int, list[tuple]] = {}
    for pid, lines in lines_by_pid.items():
        events[pid] = []
        for line in lines:
            parsed = parse_line(line)
            if parsed:
                _pid, t, event, fields = parsed
                events[pid].append((t, event, fields))
    return events


def evaluate(lines_by_pid: dict[int, list[str]]) -> tuple[bool, list[str]]:
    events = parse_all(lines_by_pid)

    states = {}
    for pid, evs in sorted(events.items()):
        alive, leader = False, None
        for _t, event, fields in evs:
            if event in ALIVE_EVENTS:
                alive, leader = True, None
            elif event in DEAD_EVENTS:
                alive = False
            elif event == "LEADER":
                leader = fields.get("leader")
        states[pid] = (alive, leader)

    alive_ids = [pid for pid, (alive, _l) in states.items() if alive]
    expected = f"p{min(alive_ids)}" if alive_ids else None

    report = [
        "Processos ativos: " + (", ".join(f"p{p}" for p in alive_ids) or "nenhum")
        + f"  |  líder esperado (menor ID ativo): {expected}"
    ]
    ok = bool(alive_ids)
    for pid, (alive, leader) in states.items():
        if not alive:
            report.append(f"  p{pid}: FALHO")
            continue
        good = leader == expected
        ok = ok and good
        report.append(f"  p{pid}: ativo   líder={leader}   {'OK' if good else 'DIVERGENTE'}")
    return ok, report


def timeline_lines(lines_by_pid: dict[int, list[str]]) -> list[str]:
    rows = []
    for pid, evs in parse_all(lines_by_pid).items():
        for t, event, fields in evs:
            if event in TIMELINE_EVENTS:
                extra = " ".join(f"{k}={v}" for k, v in fields.items())
                rows.append((t, pid, event, extra))
    rows.sort()
    if not rows:
        return []
    t0 = rows[0][0]
    return [f"  +{t - t0:8.3f}s  p{pid}  {event} {extra}".rstrip() for t, pid, event, extra in rows]


def load_logs(log_dir: str) -> dict[int, list[str]]:
    lines_by_pid = {}
    for path in sorted(glob.glob(os.path.join(log_dir, "process*.log"))):
        match = re.search(r"process(\d+)\.log$", path)
        if not match:
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines_by_pid[int(match.group(1))] = handle.read().splitlines()
    return lines_by_pid


def report(log_dir: str, timeline: bool = False) -> bool:
    lines_by_pid = load_logs(log_dir)
    if not lines_by_pid:
        print(f"Nenhum log encontrado em {log_dir!r}.")
        return False

    if timeline:
        print("Linha do tempo:")
        print("\n".join(timeline_lines(lines_by_pid)))
        print()

    ok, lines = evaluate(lines_by_pid)
    print("\n".join(lines))

    # Aviso de estabilização (heartbeats periódicos não contam como atividade): t usa time.monotonic(), comparável entre processos da mesma máquina.
    times = [t for evs in parse_all(lines_by_pid).values() for t, e, _f in evs if e != "HEARTBEAT_SENT"]
    if times and time.monotonic() - max(times) < 3.0:
        print("  (aviso: houve atividade há menos de 3s; o sistema pode ainda estar convergindo)")

    print("RESULTADO:", "OK - todos os ativos concordam no líder correto" if ok else "FALHOU")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--logs", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
    parser.add_argument("--timeline", action="store_true")
    args = parser.parse_args()
    sys.exit(0 if report(args.logs, args.timeline) else 1)


if __name__ == "__main__":
    main()
