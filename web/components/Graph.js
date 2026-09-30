function Graph({ nodes, packets, selected, onSelect }) {
  const alive = nodes.filter((n) => n.alive);
  const edges = [];
  for (let i = 0; i < alive.length; i++) {
    for (let j = i + 1; j < alive.length; j++) {
      edges.push([alive[i], alive[j]]);
    }
  }

  return (
    <svg viewBox="0 0 600 540" role="img" aria-label="Grafo dos cinco processos">
      {edges.map(([a, b]) => {
        const pa = nodePos(a.id, true), pb = nodePos(b.id, true);
        return <line key={`${a.id}-${b.id}`} className="edge" x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y} />;
      })}

      {nodes.filter((n) => !n.alive && n.status !== "OFF").map((n) => {
        const b = basePos(n.id);
        return <circle key={`g${n.id}`} className="ghost" cx={b.x} cy={b.y} r="30" />;
      })}

      {nodes.map((n) => {
        const pos = nodePos(n.id, n.alive || n.status === "OFF");
        const style = STATUS_STYLE[n.status] || STATUS_STYLE.OFF;
        const isLeader = n.alive && n.leader === n.name;
        return (
          <g
            key={n.id}
            className="node"
            tabIndex="0"
            role="button"
            aria-label={`${n.name}, ${isLeader ? "líder" : style.label}`}
            onClick={() => onSelect(n.name)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(n.name)}
          >
            <g className="node-body" style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}>
              {n.last_heartbeat > 0 && n.alive && <circle key={n.last_heartbeat} className="pulse" r="28" />}
              {selected === n.name && <circle className="selected-ring" r="39" />}
              {isLeader && <circle className="crown-ring" r="34" />}
              <circle
                className="core"
                r="27"
                fill={style.fill}
                stroke={n.alive ? "#d8f0f5" : "#6a7f87"}
                strokeWidth="2"
                strokeDasharray={n.alive ? "0" : "4 3"}
              />
              <text className="pid">{n.name}</text>
              <text className={`tag ${isLeader ? "leader" : ""} ${!n.alive && n.status === "DEAD" ? "dead" : ""}`} y="50">
                {isLeader ? "líder" : style.label}
              </text>
            </g>
          </g>
        );
      })}

      {packets.map((p) => <Packet key={p.id} p={p} />)}
    </svg>
  );
}