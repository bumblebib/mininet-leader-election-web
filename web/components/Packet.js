function Packet({ p }) {
  const [go, setGo] = React.useState(false);

  React.useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setGo(true)));
    return () => cancelAnimationFrame(id);
  }, []);

  const at = go ? { x: p.tx, y: p.ty } : { x: p.fx, y: p.fy };
  const big = p.kind !== "HEARTBEAT";

  return (
    <g
      style={{
        transform: `translate(${at.x}px, ${at.y}px)`,
        transition: `transform ${p.ms}ms ease-in-out`,
        opacity: go && p.fade ? 0.15 : 1,
      }}
    >
      <circle
        r={big ? 7 : 3.5}
        fill={PACKET_COLOR[p.kind]}
        stroke={big ? "#fff" : "none"}
        strokeWidth="1.5"
      />
    </g>
  );
}