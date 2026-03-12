import "./TextEditor.css";

interface Props {
  textLine1: string;
  textLine2: string;
  textLine3: string;
  fontPreset: number;
  mapOnly: boolean;
  onTextLine1Change: (v: string) => void;
  onTextLine2Change: (v: string) => void;
  onTextLine3Change: (v: string) => void;
  onFontPresetChange: (v: number) => void;
  onMapOnlyChange: (v: boolean) => void;
  showLine3?: boolean;
  showFontPreset?: boolean;
  showMapOnly?: boolean;
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
  mapOnly,
  onTextLine1Change,
  onTextLine2Change,
  onTextLine3Change,
  onFontPresetChange,
  onMapOnlyChange,
  showLine3 = true,
  showFontPreset = true,
  showMapOnly = false,
}: Props) {
  return (
    <div className="text-editor">
      <div className="text-header">
        <label>Text</label>
        {showMapOnly && (
          <label className="map-only-toggle">
            <input
              type="checkbox"
              checked={mapOnly}
              onChange={(e) => onMapOnlyChange(e.target.checked)}
            />
            <span>No Text — Clean Map</span>
          </label>
        )}
      </div>

      {!mapOnly && (
        <>
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
        </>
      )}
    </div>
  );
}
