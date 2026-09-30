function describe(ev) {
  const n = `p${ev.pid}`, f = ev.fields;
  switch (ev.event) {
    case "HEARTBEAT_SENT":       return ["hb", `${n} enviou heartbeat`];
    case "SEND_ELECTION":        return ["vote", `${n} → ${f.to}: ELECTION`];
    case "SEND_OK":              return ["vote", `${n} → ${f.to}: OK (tenho prioridade)`];
    case "SEND_COORDINATOR":     return ["leader", `${n} → ${f.to}: COORDINATOR`];
    case "ELECTION_START":       return ["vote", `${n} convocou uma eleição`];
    case "TRIGGER_ELECT":        return ["vote", `${n} recebeu ordem para convocar eleição`];
    case "ELECTION_TIMEOUT":     return ["leader", `${n}: nenhum nó com maior prioridade respondeu, assume a liderança`];
    case "WAIT_COORDINATOR":     return ["msg", `${n} recebeu OK e aguarda o anúncio do líder`];
    case "COORDINATOR_TIMEOUT":  return ["vote", `${n}: ninguém anunciou o líder, nova eleição`];
    case "COORDINATOR_REJECTED": return ["vote", `${n} recusou o anúncio de ${f.from} (tem prioridade)`];
    case "LEADER":               return f.leader === "none"
                                   ? ["down", `${n} ficou sem líder`]
                                   : ["leader", `${n} reconhece ${f.leader} como líder`];
    case "PEER_DOWN":            return ["down", `${n} detectou que ${f.peer} foi desconectado`];
    case "PEER_UP":              return ["up", `${n} voltou a ver ${f.peer}`];
    case "CRASH":                return ["crash", `${n} falhou (queda simulada — processo continua no SO)`];
    case "KILLED":               return ["killed", `${n} foi morto (falha real — SIGKILL no SO)`];
    case "START":                return ["up", `${n} iniciou`];
    case "RECOVER":              return ["up", `${n} se recuperou e foi reinserido`];
    default:                     return null;
  }
}