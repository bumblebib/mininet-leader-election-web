function Controls({ node, controllable, onCommand, busy }) {
  if (!node) return <div className="controls"><h2>Clique em um processo para controlá-lo e inspecioná-lo</h2></div>;
  const can = controllable && !busy;
  const alive = node.alive;

  return (
    <div className="controls">
      <h2>{node.name} selecionado</h2>
      <div className="btns">
        <button className="danger" disabled={!can || !alive} onClick={() => onCommand("crash", node.name)}>Simular queda</button>
        <button disabled={!can || node.down_kind !== "crash"} onClick={() => onCommand("recover", node.name)}>Recuperar</button>
        <button disabled={!can || !alive} onClick={() => onCommand("elect", node.name)}>Forçar eleição</button>
        <button className="danger" disabled={!can || !alive} onClick={() => onCommand("kill", node.name)}>Matar processo</button>
        <button disabled={!can || node.down_kind !== "killed"} onClick={() => onCommand("restart", node.name)}>Reiniciar processo</button>
      </div>
      <NodeInspector node={node} />
      {!controllable && <div className="note">Modo somente leitura. Para usar os botões, inicie com: sudo python3 mininet_topology.py --web</div>}
    </div>
  );
}