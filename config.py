"""Parâmetros compartilhados por todos os componentes do projeto."""

NUM_PROCESSES = 5

# Rede (Mininet): o servidor é 10.0.0.1 e o processo pN é 10.0.0.(N+1)
PORT = 5000
SERVER_IP = "10.0.0.1"
SERVER_PORT = 5000
CONTROL_IP = "127.0.0.1"
CONTROL_PORT = 9000

# Tempos (segundos).
#   ELECTION_TIMEOUT     : quanto o iniciador espera por um OK antes de assumir a liderança.
#                          Precisa ser bem maior que o RTT (com LINK_DELAY=5ms o RTT é ~20ms).
#   COORDINATOR_TIMEOUT  : depois de receber um OK, quanto espera pelo COORDINATOR.
#                          Precisa ser maior que ELECTION_TIMEOUT (o processo menor que
#                          respondeu OK ainda vai esperar o próprio timeout de eleição).
#   HEARTBEAT_INTERVAL   : período de envio dos heartbeats.
#   PEER_TIMEOUT         : sem ouvir nada de um processo por esse tempo => removido da visão.
#   TICK_INTERVAL        : período do "relógio" que confere heartbeats e prazos.
HEARTBEAT_INTERVAL = 0.5
PEER_TIMEOUT = 2.0
ELECTION_TIMEOUT = 1.0
COORDINATOR_TIMEOUT = 3.0
TICK_INTERVAL = 0.1

LINK_DELAY = "5ms"


def ip_of(process_id: int) -> str:
    return f"10.0.0.{process_id + 1}"


def peers() -> dict[str, tuple[str, int]]:
    return {f"p{i}": (ip_of(i), PORT) for i in range(1, NUM_PROCESSES + 1)}
