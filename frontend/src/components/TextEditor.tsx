import "./TextEditor.css";

interface Props {
  textLine1: string;
  textLine2: string;
  textLine3: string;
  fontPreset: number;
  onTextLine1Change: (v: string) => void;
  onTextLine2Change: (v: string) => void;
  onTextLine3Change: (v: string) => void;
  onFontPresetChange: (v: number) => void;
  showLine3?: boolean;
  showFontPreset?: boolean;
}

const FONT_PRESETS: { id: number; label: string; description: string }[] = [
  { id: 1, label: "Sans", description: "Montserrat + Roboto" },
  { id: 2, label: "Serif", description: "Playfair Display" },
  { id: 3, label: "Script", description: "Pinyon Script" },
  { id: 4, label: "Cursive", description: "Dancing Script" },
  { id: 5, label: "Classic", description: "Cormorant Garamond" },
];

export default function TextEditor({
  textLine1,
  textLine2,
  textLine3,
  fontPreset,
  onTextLine1Change,
  onTextLine2Change,
  onTextLine3Change,
  onFontPresetChange,
  showLine3 = true,
  showFontPreset = true,
}: Props) {
  return (
    <div className="text-editor">
      <label>Text</label>

      <div className="text-field">
        <span className="text-field-label">Line 1 (large)</span>
        <input
          type="text"
          value={textLine1}
          onChange={(e) => onTextLine1Change(e.target.value)}
          placeholder="City name or custom title"
        />
      </div>

      <div className="text-field">
        <span className="text-field-label">Line 2 (medium)</span>
        <input
          type="text"
          value={textLine2}
          onChange={(e) => onTextLine2Change(e.target.value)}
          placeholder="Country or subtitle"
        />
      </div>

      {showLine3 && (
        <div className="text-field">
          <span className="text-field-label">Line 3 (small)</span>
          <input
            type="text"
            value={textLine3}
            onChange={(e) => onTextLine3Change(e.target.value)}
            placeholder="e.g. Est. June 2019"
          />
        </div>
      )}

      {showFontPreset && <div className="font-preset-section">
        <span className="font-preset-label">Font Preset</span>
        <div className="font-preset-options">
          {FONT_PRESETS.map((f) => (
            <button
              key={f.id}
              className={`font-preset-btn ${fontPreset === f.id ? "active" : ""}`}
              onClick={() => onFontPresetChange(f.id)}
              title={f.description}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>}
    </div>
  );
}
