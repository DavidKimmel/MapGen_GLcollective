import { useState, useRef, useCallback, useEffect } from "react";
import { submitGenerate, pollStatus, downloadUrl, exportGelato } from "../api/client";
import type { PosterSettings, GeoResult, JobStatus } from "../types";
import "./DownloadPanel.css";

interface Props {
  city: GeoResult | null;
  center: [number, number];
  theme: string;
  settings: PosterSettings;
  displayCity: string;
  displaySubtitle: string;
  pinLat: number | null;
  pinLon: number | null;
  onPosterReady: (jobId: string, outputFile: string | null) => void;
}

export default function DownloadPanel({
  city, center, theme, settings, displayCity, displaySubtitle, pinLat, pinLon, onPosterReady,
}: Props) {
  const [status, setStatus] = useState<"idle" | "generating" | "complete" | "error">("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [outputFile, setOutputFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gelatoStatus, setGelatoStatus] = useState<"idle" | "exporting" | "done" | "error">("idle");
  const [gelatoError, setGelatoError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => stopPolling, [stopPolling]);

  async function handleGenerate() {
    if (!city) return;
    setStatus("generating");
    setError(null);
    setJobId(null);
    setOutputFile(null);
    setGelatoStatus("idle");
    setGelatoError(null);
    stopPolling();

    const sizeStr = `${settings.width}x${settings.height}`;

    try {
      const id = await submitGenerate({
        city: displayCity || city.city,
        country: city.country,
        lat: center[0],
        lon: center[1],
        distance: settings.distance,
        theme,
        size: sizeStr,
        crop: settings.crop,
        detail_layers: settings.detail_layers,
        pin_lat: pinLat,
        pin_lon: pinLon,
        pin_style: settings.pin_style,
        pin_color: settings.pin_color || undefined,
        font_preset: settings.font_preset,
        text_line_1: settings.text_line_1 || displayCity || undefined,
        text_line_2: settings.text_line_2 || displaySubtitle || undefined,
        text_line_3: settings.text_line_3 || undefined,
        border: settings.border,
      });
      setJobId(id);

      pollingRef.current = setInterval(async () => {
        try {
          const s: JobStatus = await pollStatus(id);
          if (s.status === "complete") {
            setStatus("complete");
            setOutputFile(s.output_file);
            stopPolling();
            onPosterReady(id, s.output_file);
          } else if (s.status === "error") {
            setStatus("error");
            setError(s.error);
            stopPolling();
          }
        } catch {
          setStatus("error");
          setError("Lost connection to server");
          stopPolling();
        }
      }, 2000);
    } catch {
      setStatus("error");
      setError("Failed to submit job");
    }
  }

  async function handleGelatoExport() {
    if (!jobId) return;
    setGelatoStatus("exporting");
    setGelatoError(null);
    try {
      await exportGelato(jobId);
      setGelatoStatus("done");
    } catch (e) {
      setGelatoStatus("error");
      setGelatoError(e instanceof Error ? e.message : "Export failed");
    }
  }

  const fileName = outputFile
    ? outputFile.replace(/\\/g, "/").split("/").pop()
    : null;

  return (
    <div className="download-panel">
      <button
        className="generate-btn"
        onClick={handleGenerate}
        disabled={!city || status === "generating"}
      >
        {status === "generating" ? "Generating..." : "Generate Poster"}
      </button>

      {status === "generating" && (
        <div className="status-msg">
          <span className="spinner" /> Processing... this may take a few minutes.
        </div>
      )}

      {status === "complete" && jobId && (
        <>
          <div className="status-msg success">
            Poster ready!
            {fileName && <span className="file-name">{fileName}</span>}
          </div>
          <div className="action-row">
            <a href={downloadUrl(jobId)} download className="action-btn download">
              Download
            </a>
            <button
              className="action-btn gelato"
              onClick={handleGelatoExport}
              disabled={gelatoStatus === "exporting"}
            >
              {gelatoStatus === "exporting" ? "Exporting..." : "Export for Gelato"}
            </button>
          </div>
          {gelatoStatus === "done" && (
            <div className="status-msg gelato-success">
              Gelato files exported to gelato_ready/
            </div>
          )}
          {gelatoStatus === "error" && (
            <div className="status-msg error-msg">
              Gelato: {gelatoError}
            </div>
          )}
        </>
      )}

      {status === "error" && (
        <div className="status-msg error-msg">Error: {error}</div>
      )}
    </div>
  );
}
