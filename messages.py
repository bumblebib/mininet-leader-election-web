"""Mensagens do algoritmo do Valentão (Bully) e sua serialização em JSON sobre UDP."""

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Election:
    """Convocação de eleição (enviada só a processos de ID menor)."""
    sender: str


@dataclass(frozen=True)
class Ok:
    """Resposta a um ELECTION: 'estou vivo e tenho prioridade sobre você'."""
    sender: str


@dataclass(frozen=True)
class Coordinator:
    """Anúncio do novo líder."""
    sender: str


@dataclass(frozen=True)
class Heartbeat:
    """Sinal de vida usado pelo detector de falhas."""
    sender: str


@dataclass(frozen=True)
class Trigger:
    """Comando do servidor para um processo (não faz parte do algoritmo)."""
    action: str  # CRASH | RECOVER | ELECT | STATUS
    sender: str = "server"


_TYPES = {
    "ELECTION": Election,
    "OK": Ok,
    "COORDINATOR": Coordinator,
    "HEARTBEAT": Heartbeat,
    "TRIGGER": Trigger,
}
_NAMES = {cls: name for name, cls in _TYPES.items()}


def serialize(packet) -> bytes:
    data = asdict(packet)
    data["type"] = _NAMES[type(packet)]
    return json.dumps(data).encode("utf-8")


def deserialize(data: bytes):
    fields = json.loads(data.decode("utf-8"))
    kind = fields.pop("type")
    return _TYPES[kind](**fields)
