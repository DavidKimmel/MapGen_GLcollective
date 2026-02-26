import "./DetailToggle.css";

interface Props {
  enabled: boolean;
  onChange: (v: boolean) => void;
}

export default function DetailToggle({ enabled, onChange }: Props) {
  return (
    <div className="detail-toggle">
      <label className="toggle-label">
        <span className="toggle-text">
          Detail Layers
          <span className="toggle-hint">
            {enabled ? "All 11 layers (ocean, railways, buildings...)" : "Minimal (roads, water, parks)"}
          </span>
        </span>
        <span className={`toggle-switch ${enabled ? "on" : ""}`} onClick={() => onChange(!enabled)}>
          <span className="toggle-knob" />
        </span>
      </label>
    </div>
  );
}
