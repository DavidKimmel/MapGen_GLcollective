import type { CropShape } from "../types";
import "./CropSelector.css";

interface Props {
  value: CropShape;
  onChange: (crop: CropShape) => void;
}

const CROPS: { id: CropShape; label: string; icon: string }[] = [
  { id: "full", label: "Full", icon: "\u25a1" },
  { id: "circle", label: "Circle", icon: "\u25cb" },
  { id: "heart", label: "Heart", icon: "\u2661" },
  { id: "house", label: "House", icon: "\u2302" },
];

export default function CropSelector({ value, onChange }: Props) {
  return (
    <div className="crop-selector">
      <label>Crop Shape</label>
      <div className="crop-options">
        {CROPS.map((c) => (
          <button
            key={c.id}
            className={`crop-btn ${value === c.id ? "active" : ""}`}
            onClick={() => onChange(c.id)}
            title={c.label}
          >
            <span className="crop-icon">{c.icon}</span>
            <span className="crop-label">{c.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
