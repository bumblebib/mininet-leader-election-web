"""Algoritmo do Valentão (Bully) com regra invertida: MENOR ID vence.

Este módulo contém só a lógica, sem sockets nem threads próprias. Tudo que é
externo é injetado:
    send(packet, dest_name)  -> envia um pacote
    now()                    -> tempo atual em segundos
    log(line)                -> recebe cada linha de log já formatada

Assim a mesma lógica roda em produção (UDP + Mininet, ver process.py) e pode ser
exercitada em memória (fila de pacotes + relógio simulado), sem sockets.

Estados de um processo:
    NORMAL      : sem eleição em andamento
    ELECTING    : mandou ELECTION aos menores e espera OK até um prazo
    WAIT_COORD  : recebeu OK; espera o COORDINATOR até outro prazo
    DEAD        : falhou (ignora tudo, exceto o comando RECOVER)

Tolerância a falhas (detector por heartbeat):
    - todo processo envia HEARTBEAT a todos os outros periodicamente;
    - qualquer mensagem recebida de q atualiza last_seen[q];
    - q sem mensagens por PEER_TIMEOUT => removido da visão (PEER_DOWN);
    - q volta a enviar mensagens          => reinserido na visão (PEER_UP);
    - se o líder é removido, dispara-se uma eleição.
"""

import threading

import config
from messages import Coordinator, Election, Heartbeat, Ok, Trigger

NORMAL, ELECTING, WAIT_COORD, DEAD = "NORMAL", "ELECTING", "WAIT_COORD", "DEAD"


def process_number(name: str) -> int:
    return int(name[1:])


class BullyNode:
    def __init__(
        self,
        process_id: int,
        num_processes: int,
        send,
        now,
        log=None,
        heartbeat_interval: float = config.HEARTBEAT_INTERVAL,
        peer_timeout: float = config.PEER_TIMEOUT,
        election_timeout: float = config.ELECTION_TIMEOUT,
        coordinator_timeout: float = config.COORDINATOR_TIMEOUT,
        log_heartbeats: bool = False,
    ):
        self.id = process_id
        self.name = f"p{process_id}"
        everyone = [f"p{i}" for i in range(1, num_processes + 1)]
        self.others = [n for n in everyone if n != self.name]
        self.lower = [n for n in everyone if process_number(n) < self.id]

        self.send = send
        self.now = now
        self._emit = log or (lambda line: print(line, flush=True))

        self.heartbeat_interval = heartbeat_interval
        self.peer_timeout = peer_timeout
        self.election_timeout = election_timeout
        self.coordinator_timeout = coordinator_timeout
        # Opt-in (usado pela visualização web): uma linha HEARTBEAT_SENT por rodada de envio.
        self.log_heartbeats = log_heartbeats

        # RLock: a mesma thread pode reentrar (ex.: start_election -> _become_leader)
        self.lock = threading.RLock()
        self._reset()

    # ------------------------------------------------------------------ util
    def _reset(self):
        self.state = NORMAL
        self.leader: str | None = None
        self.alive: dict[str, float] = {}  # visão de membros: nome -> last_seen
        self.deadline: float | None = None
        self.next_heartbeat = self.now()

    def log(self, event: str, extra: str = ""):
        line = f"[{self.name}] t={self.now():.3f} {event}"
        if extra:
            line += f" {extra}"
        self._emit(line)

    def _send(self, packet, dest: str):
        kind = {Election: "SEND_ELECTION", Ok: "SEND_OK", Coordinator: "SEND_COORDINATOR"}[type(packet)]
        self.log(kind, f"to={dest}")
        self.send(packet, dest)

    def _set_leader(self, leader: str | None):
        if leader != self.leader:
            self.leader = leader
            self.log("LEADER", f"leader={leader or 'none'}")

    def _touch(self, sender: str):
        if sender not in self.alive:
            self.log("PEER_UP", f"peer={sender}")
        self.alive[sender] = self.now()

    # ------------------------------------------------------------ ciclo de vida
    def start(self):
        """Início do processo (boot ou reinício real): sempre dispara eleição."""
        with self.lock:
            self._reset()
            self.log("START")
            self.start_election()

    def crash(self):
        """Falha simulada: para de responder e de enviar heartbeats."""
        with self.lock:
            if self.state == DEAD:
                self.log("IGNORED", "action=CRASH reason=already_dead")
                return
            self.log("CRASH")
            self.state = DEAD
            self.leader = None
            self.alive = {}
            self.deadline = None

    def recover(self):
        """Recuperação: volta com estado limpo e dispara eleição (retoma a liderança se for o menor)."""
        with self.lock:
            if self.state != DEAD:
                self.log("IGNORED", "action=RECOVER reason=not_dead")
                return
            self.log("RECOVER")
            self._reset()
            self.start_election()

    # ------------------------------------------------------------------ eleição
    def start_election(self):
        with self.lock:
            if self.state in (ELECTING, DEAD):
                return
            self.log("ELECTION_START")
            if not self.lower:
                # Ninguém com ID menor: não há a quem perguntar, vence direto.
                self._become_leader()
                return
            # Estado e prazo ANTES de enviar: uma resposta imediata já encontra tudo pronto.
            self.state = ELECTING
            self.deadline = self.now() + self.election_timeout
            for name in self.lower:
                self._send(Election(self.name), name)

    def _become_leader(self):
        self.state = NORMAL
        self.deadline = None
        self._set_leader(self.name)
        for name in self.others:
            self._send(Coordinator(self.name), name)

    # ---------------------------------------------------------------- recepção
    def handle(self, packet):
        with self.lock:
            if isinstance(packet, Trigger):
                self._handle_trigger(packet.action)
                return
            if self.state == DEAD:
                return

            self._touch(packet.sender)

            if isinstance(packet, Heartbeat):
                return
            if isinstance(packet, Election):
                self._on_election(packet.sender)
            elif isinstance(packet, Ok):
                self._on_ok(packet.sender)
            elif isinstance(packet, Coordinator):
                self._on_coordinator(packet.sender)
            else:
                raise TypeError(f"Unsupported packet: {packet}")

    def _on_election(self, sender: str):
        self.log("RECV_ELECTION", f"from={sender}")
        if process_number(sender) < self.id:
            # ELECTION só deveria vir de IDs maiores; ignora.
            self.log("IGNORED", f"action=ELECTION from={sender} reason=lower_id")
            return
        self._send(Ok(self.name), sender)
        # Já estou em eleição (ou esperando um menor anunciar)? Não reinicia.
        if self.state == NORMAL:
            self.start_election()

    def _on_ok(self, sender: str):
        self.log("RECV_OK", f"from={sender}")
        if self.state == ELECTING:
            self.state = WAIT_COORD
            self.deadline = self.now() + self.coordinator_timeout
            self.log("WAIT_COORDINATOR", f"timeout={self.coordinator_timeout}")

    def _on_coordinator(self, sender: str):
        self.log("RECV_COORDINATOR", f"from={sender}")
        if process_number(sender) > self.id:
            # Um ID maior se declarou líder, mas eu tenho prioridade: disputo.
            self.log("COORDINATOR_REJECTED", f"from={sender}")
            if self.state == NORMAL:
                self.start_election()
            return
        self.state = NORMAL
        self.deadline = None
        self._set_leader(sender)

    def _handle_trigger(self, action: str):
        if action == "CRASH":
            self.crash()
        elif action == "RECOVER":
            self.recover()
        elif action == "ELECT":
            if self.state == DEAD:
                self.log("IGNORED", "action=ELECT reason=dead")
            else:
                self.log("TRIGGER_ELECT")
                self.start_election()
        elif action == "STATUS":
            alive = ",".join(sorted(self.alive)) or "-"
            self.log("STATUS", f"state={self.state} leader={self.leader or 'none'} alive={alive}")
        else:
            self.log("IGNORED", f"action={action} reason=unknown")

    # -------------------------------------------------------------------- tick
    def tick(self):
        """Chamado periodicamente: heartbeats, detector de falhas e prazos."""
        with self.lock:
            if self.state == DEAD:
                return
            now = self.now()

            # 1) heartbeats para TODOS (inclusive os que estão fora da visão: é assim que voltam)
            if now >= self.next_heartbeat:
                for name in self.others:
                    self.send(Heartbeat(self.name), name)
                if self.log_heartbeats:
                    self.log("HEARTBEAT_SENT")
                self.next_heartbeat = now + self.heartbeat_interval

            # 2) detector de falhas
            for name in list(self.alive):
                if now - self.alive[name] > self.peer_timeout:
                    del self.alive[name]
                    self.log("PEER_DOWN", f"peer={name}")
                    if name == self.leader:
                        self._set_leader(None)
                        if self.state == NORMAL:
                            self.start_election()

            # 3) prazos de eleição
            if self.deadline is not None and now >= self.deadline:
                if self.state == ELECTING:
                    self.log("ELECTION_TIMEOUT")
                    self._become_leader()
                elif self.state == WAIT_COORD:
                    self.log("COORDINATOR_TIMEOUT")
                    self.state = NORMAL
                    self.deadline = None
                    self.start_election()
