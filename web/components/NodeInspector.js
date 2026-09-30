function NodeInspector({ node }) {
  if (!node) return null;
  const isCrash = node.down_kind === "crash";
  const isKilled = node.down_kind === "killed";
  const ip = `10.0.0.${node.id + 1}`;

  return (
    <div className="node-inspector">
      <div className="inspector-title">Inspeção no SO & Rede ({node.name})</div>
      <div className="inspector-grid">
        <div className="inspector-item">
          <span className="label">Processo SO:</span>
          <span className={`val ${node.alive ? "st-ok" : isCrash ? "st-warn" : "st-err"}`}>
            {node.alive 
              ? `Ativo (PID: ${node.os_pid || "..."})` 
              : isCrash 
                ? `Em execução / Silenciado (PID: ${node.os_pid || "..."})` 
                : isKilled
                  ? "Encerrado (Sem PID)"
                  : "Aguardando"}
          </span>
        </div>
        <div className="inspector-item">
          <span className="label">Socket UDP ({ip}:5000):</span>
          <span className={`val ${node.alive || isCrash ? "st-ok" : "st-err"}`}>
            {node.alive || isCrash ? "Aberto / Listening" : "Fechado / Porta livre"}
          </span>
        </div>
        <div className="inspector-item">
          <span className="label">Canal de Controle:</span>
          <span className={`val ${node.alive || isCrash ? "st-ok" : "st-err"}`}>
            {node.alive || isCrash ? "Ativo (Aceita Trigger)" : "Inalcançável"}
          </span>
        </div>
        <div className="inspector-item">
          <span className="label">Host Mininet:</span>
          <span className="val st-ok">Ativo (IP {ip})</span>
        </div>
      </div>
    </div>
  );
}