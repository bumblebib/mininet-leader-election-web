const { useState, useEffect, useRef, useMemo } = React;

function App() {
  const [nodes, setNodes] = useState(() =>
    Array.from({ length: N }, (_, i) => ({ id: i + 1, name: `p${i + 1}`, alive: false, status: "OFF", leader: null, last_heartbeat: 0 })));
  const [feed, setFeed] = useState([]);
  const [packets, setPackets] = useState([]);
  const [info, setInfo] = useState({ converged: false, expected: null, controllable: false });
  const [online, setOnline] = useState(true);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showHb, setShowHb] = useState(true);
  const [showMsg, setShowMsg] = useState(true);
  const [showLife, setShowLife] = useState(true);

  const seq = useRef(0);
  const first = useRef(true);
  const t0 = useRef(null);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  useEffect(() => {
    let stop = false, inflight = false;
    const tick = async () => {
      if (inflight) return;
      inflight = true;
      try {
        const res = await fetch(`/api/state?since=${seq.current}`);
        const data = await res.json();
        if (stop) return;
        setOnline(true);
        if (data.reset) { setFeed([]); t0.current = null; first.current = true; }
        seq.current = data.seq;
        setNodes(data.nodes);
        setInfo({ converged: data.converged, expected: data.expected_leader, controllable: data.controllable });

        const evs = data.events;
        if (evs.length) {
          if (t0.current === null) t0.current = evs[0].t;
          const rows = [];
          for (const ev of evs) {
            const d = describe(ev);
            if (d) rows.push({ seq: ev.seq, rel: ev.t - t0.current, cls: d[0], text: d[1], event: ev.event });
          }
          setFeed((old) => [...rows.reverse(), ...old].slice(0, 400));

          if (!first.current) {
            const now = performance.now();
            const alive = Object.fromEntries(nodesRef.current.map((n) => [n.id, n.alive]));
            const fresh = [];
            for (const ev of evs.slice(-80)) {
              const mk = (to, kind, ms, fade) => {
                const a = nodePos(ev.pid, alive[ev.pid]), b = nodePos(to, alive[to]);
                fresh.push({ id: `${ev.seq}-${to}`, kind, fx: a.x, fy: a.y, tx: b.x, ty: b.y, ms, fade, born: now });
              };
              const kind = { SEND_ELECTION: "ELECTION", SEND_OK: "OK", SEND_COORDINATOR: "COORDINATOR" }[ev.event];
              if (kind && ev.fields.to) mk(parseInt(ev.fields.to.slice(1), 10), kind, 700, !alive[parseInt(ev.fields.to.slice(1), 10)]);
              else if (ev.event === "HEARTBEAT_SENT")
                for (let id = 1; id <= N; id++) if (id !== ev.pid && alive[id] && alive[ev.pid]) mk(id, "HEARTBEAT", 600, false);
            }
            if (fresh.length) setPackets((old) => [...old, ...fresh].slice(-150));
          }
          first.current = false;
        }
      } catch (e) {
        if (!stop) setOnline(false);
      } finally {
        inflight = false;
      }
    };
    tick();
    const poll = setInterval(tick, 250);
    const sweep = setInterval(() => setPackets((old) => old.filter((p) => performance.now() - p.born < 1200)), 400);
    return () => { stop = true; clearInterval(poll); clearInterval(sweep); };
  }, []);

  const onCommand = async (action, target) => {
    setBusy(true);
    try {
      const res = await fetch("/api/command", { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ action, target }) });
      if (!res.ok) throw new Error((await res.json()).error || "erro");
    } catch (e) {
      alert(`Não foi possível executar o comando: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const anyAlive = nodes.some((n) => n.alive);
  const badge = !anyAlive ? { cls: "off", text: "Sem processos ativos" }
    : info.converged ? { cls: "ok", text: `Todos concordam: líder ${info.expected}` }
    : { cls: "wait", text: "Elegendo…" };

  const visible = useMemo(() => feed.filter((r) => {
    if (r.event === "HEARTBEAT_SENT") return showHb;
    if (r.event.startsWith("SEND_")) return showMsg;
    if (["CRASH", "KILLED", "START", "RECOVER", "PEER_DOWN", "PEER_UP"].includes(r.event)) return showLife;
    return true;
  }), [feed, showHb, showMsg, showLife]);

  return (
    <div className="app">
      <section className="stage">
        <div className="top">
          <h1>Eleição de líder — Fracão (menor ID vence)</h1>
          <span className={`badge ${badge.cls}`} aria-live="polite">{badge.text}</span>
        </div>
        <div className="graph">
          <Graph nodes={nodes} packets={packets} selected={selected} onSelect={setSelected} />
        </div>
        <div className="legend">
          <span><i style={{ background: PACKET_COLOR.HEARTBEAT }} />heartbeat</span>
          <span><i style={{ background: PACKET_COLOR.ELECTION }} />ELECTION</span>
          <span><i style={{ background: PACKET_COLOR.OK }} />OK</span>
          <span><i style={{ background: PACKET_COLOR.COORDINATOR }} />COORDINATOR</span>
        </div>
        <Controls node={nodes.find((n) => n.name === selected)} controllable={info.controllable} busy={busy} onCommand={onCommand} />
      </section>

      <Feed
        visible={visible}
        online={online}
        showHb={showHb}
        setShowHb={setShowHb}
        showMsg={showMsg}
        setShowMsg={setShowMsg}
        showLife={showLife}
        setShowLife={setShowLife}
      />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);