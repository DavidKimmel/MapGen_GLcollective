import { downloadUrl } from "../api/client";
import "./PosterPreview.css";

interface Props {
  jobId: string | null;
  outputFile: string | null;
}

export default function PosterPreview({ jobId, outputFile }: Props) {
  if (!jobId) {
    return (
      <div className="poster-preview">
        <div className="preview-placeholder">
          Generate a poster to see preview
        </div>
      </div>
    );
  }

  const imgSrc = downloadUrl(jobId);
  const fileName = outputFile
    ? outputFile.replace(/\\/g, "/").split("/").pop()
    : null;

  return (
    <div className="poster-preview">
      <div className="preview-toolbar">
        {fileName && (
          <span className="file-path">Saved: {fileName}</span>
        )}
        <a href={imgSrc} download className="download-link">
          Download
        </a>
      </div>
      <div className="preview-container">
        <img
          src={imgSrc}
          alt="Generated poster"
          className="preview-img"
        />
      </div>
    </div>
  );
}
