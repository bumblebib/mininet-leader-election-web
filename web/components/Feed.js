function Feed({ visible, online, showHb, setShowHb, showMsg, setShowMsg, showLife, setShowLife }) {
  return (
    <aside className="feed">
      {!online && <div className="banner">Sem conexão com o backend. Tentando de novo…</div>}
      <header>
        <h2>Mensagens em tempo real</h2>
        <div className="filters">
          <label><input type="checkbox" checked={showHb} onChange={(e) => setShowHb(e.target.checked)} />heartbeats</label>
          <label><input type="checkbox" checked={showMsg} onChange={(e) => setShowMsg(e.target.checked)} />mensagens</label>
          <label><input type="checkbox" checked={showLife} onChange={(e) => setShowLife(e.target.checked)} />ciclo de vida / falhas</label>
        </div>
      </header>
      {visible.length === 0 ? (
        <div className="empty">Nenhum evento ainda. Suba a rede e as mensagens aparecem aqui.</div>
      ) : (
        <ul className="rows" aria-live="off">
          {visible.slice(0, 250).map((r) => (
            <li key={r.seq} className={`row ${r.cls}`}>
              <time>+{r.rel.toFixed(1)}s</time>
              <span>{r.text}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}