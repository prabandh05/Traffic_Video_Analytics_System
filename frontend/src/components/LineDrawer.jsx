import { useState, useRef, useEffect, useCallback } from 'react';
import { getFirstFrame, setCountingLine } from '../api';

export default function LineDrawer({ jobId, videoName, onDone, onCancel }) {
  const [frameUrl, setFrameUrl] = useState(null);
  const [points, setPoints] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const canvasRef = useRef(null);
  const imgRef = useRef(null);

  // Load first frame
  useEffect(() => {
    let cancelled = false;
    getFirstFrame(jobId)
      .then((url) => {
        if (!cancelled) setFrameUrl(url);
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load video frame');
      });
    return () => { cancelled = true; };
  }, [jobId]);

  // Draw on canvas
  const drawOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw points
    points.forEach((pt, i) => {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 8, 0, Math.PI * 2);
      ctx.fillStyle = i === 0 ? '#10b981' : '#ef4444';
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      ctx.font = 'bold 14px Inter, sans-serif';
      ctx.fillStyle = '#fff';
      ctx.fillText(i === 0 ? 'A' : 'B', pt.x + 12, pt.y - 12);
    });

    // Draw line
    if (points.length === 2) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      ctx.lineTo(points[1].x, points[1].y);
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 6]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Label
      const mx = (points[0].x + points[1].x) / 2;
      const my = (points[0].y + points[1].y) / 2;
      ctx.font = 'bold 13px Inter, sans-serif';
      ctx.fillStyle = '#f59e0b';
      ctx.fillText('Counting Line', mx + 10, my - 10);
    }
  }, [points]);

  useEffect(() => {
    drawOverlay();
  }, [points, drawOverlay]);

  const handleCanvasClick = (e) => {
    if (points.length >= 2) return;

    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;

    const rect = canvas.getBoundingClientRect();
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    setPoints((prev) => [...prev, { x: Math.round(x), y: Math.round(y) }]);
  };

  const handleReset = () => {
    setPoints([]);
    setError('');
  };

  const handleConfirm = async () => {
    if (points.length !== 2) return;
    setSaving(true);
    setError('');
    try {
      await setCountingLine(jobId, points[0].x, points[0].y, points[1].x, points[1].y);
      onDone();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save line');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="line-drawer-overlay" onClick={(e) => e.target === e.currentTarget && onCancel()}>
      <div className="line-drawer-modal">
        <h2>✏️ Draw Counting Line — {videoName}</h2>
        <p className="instructions">
          Click <strong>two points</strong> on the frame to define the counting line.
          Vehicles crossing this line will be counted.
        </p>

        {error && <div className="error-msg">{error}</div>}

        {frameUrl ? (
          <div className="line-drawer-canvas-wrap" onClick={handleCanvasClick}>
            <img
              ref={imgRef}
              src={frameUrl}
              alt="First frame"
              onLoad={drawOverlay}
              draggable={false}
            />
            <canvas ref={canvasRef} />
          </div>
        ) : (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            {error ? '❌ Error loading frame' : '⏳ Loading frame...'}
          </div>
        )}

        <div className="line-drawer-actions">
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleReset}
            disabled={points.length === 0}
          >
            🔄 Reset
          </button>
          <button
            className="btn btn-primary"
            onClick={handleConfirm}
            disabled={points.length !== 2 || saving}
          >
            {saving ? '⏳ Saving...' : '✅ Confirm Line'}
          </button>
        </div>

        {points.length > 0 && (
          <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {points.map((p, i) => (
              <span key={i} style={{ marginRight: '1rem' }}>
                Point {i === 0 ? 'A' : 'B'}: ({p.x}, {p.y})
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
