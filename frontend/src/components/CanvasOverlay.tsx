import { useRef, useEffect, useState, useCallback } from "react";
import "./CanvasOverlay.css";

interface Props {
  aspectRatio: number;
  color: string;
}

interface FrameRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

const PADDING = 24;

function computeFrame(containerW: number, containerH: number, aspectRatio: number): FrameRect {
  const availW = containerW - PADDING * 2;
  const availH = containerH - PADDING * 2;

  let w: number;
  let h: number;

  if (availW / availH > aspectRatio) {
    // Container is wider than needed — height is the constraint
    h = availH;
    w = h * aspectRatio;
  } else {
    // Container is taller than needed — width is the constraint
    w = availW;
    h = w / aspectRatio;
  }

  return {
    x: (containerW - w) / 2,
    y: (containerH - h) / 2,
    w,
    h,
  };
}

/**
 * Fixed CSS overlay that masks the area outside the poster frame.
 * The frame stays centered on screen; the user pans the map underneath.
 */
export default function CanvasOverlay({ aspectRatio, color }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [frame, setFrame] = useState<FrameRect>({ x: 0, y: 0, w: 0, h: 0 });

  const updateFrame = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    setFrame(computeFrame(el.clientWidth, el.clientHeight, aspectRatio));
  }, [aspectRatio]);

  useEffect(() => {
    updateFrame();
    const el = containerRef.current;
    if (!el) return;

    const ro = new ResizeObserver(updateFrame);
    ro.observe(el);
    return () => ro.disconnect();
  }, [updateFrame]);

  return (
    <div className="canvas-overlay" ref={containerRef}>
      <svg width="100%" height="100%" className="canvas-overlay-svg">
        <defs>
          <mask id="frame-mask">
            <rect width="100%" height="100%" fill="white" />
            <rect
              x={frame.x}
              y={frame.y}
              width={frame.w}
              height={frame.h}
              fill="black"
              rx="2"
              ry="2"
            />
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="rgba(255,255,255,0.55)"
          mask="url(#frame-mask)"
        />
      </svg>
      <div
        className="frame-border"
        style={{
          left: frame.x,
          top: frame.y,
          width: frame.w,
          height: frame.h,
          borderColor: color,
        }}
      />
    </div>
  );
}
