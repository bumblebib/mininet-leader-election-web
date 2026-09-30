const N = 5, CX = 300, CY = 270, R = 190, OUT = 52;

const angle = (id) => -Math.PI / 2 + ((id - 1) * 2 * Math.PI) / N;

const basePos = (id) => ({
  x: CX + R * Math.cos(angle(id)),
  y: CY + R * Math.sin(angle(id)),
});

const nodePos = (id, alive) => {
  const r = alive ? R : R + OUT;
  return {
    x: CX + r * Math.cos(angle(id)),
    y: CY + r * Math.sin(angle(id)),
  };
};

const STATUS_STYLE = {
  NORMAL:     { fill: "#1f7a8c", label: "ativo" },
  ELECTING:   { fill: "#7a5fd6", label: "em eleição" },
  WAIT_COORD: { fill: "#5a6fd6", label: "aguarda líder" },
  DEAD:       { fill: "#4a5a61", label: "desconectado" },
  OFF:        { fill: "#4a5a61", label: "aguardando" },
};

const PACKET_COLOR = {
  ELECTION: "#a98cff",
  OK: "#7fd0ff",
  COORDINATOR: "#f5b83d",
  HEARTBEAT: "#5fd6b8",
};