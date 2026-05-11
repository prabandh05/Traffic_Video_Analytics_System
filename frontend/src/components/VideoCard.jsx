import { useState } from 'react';
import { startProcessing, deleteVideo, getExcelDownloadUrl, getCsvDownloadUrl } from '../api';

export default function VideoCard({ video, onDrawLine, onRefresh }) {
  const [loading, setLoading] = useState(false);

  const statusClass = video.status.toLowerCase();
  const hasLine = video.line_start && video.line_end;
  const isCompleted = video.status === 'Completed';
  const isPending = video.status === 'Pending';
  const isProcessing = video.status === 'Processing';
  const isFailed = video.status === 'Failed';

  const handleProcess = async () => {
    setLoading(true);
    try {
      await startProcessing(video.job_id);
      onRefresh();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start processing');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${video.video_name}?`)) return;
    try {
      await deleteVideo(video.job_id);
      onRefresh();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const progressPercent = video.total_frames > 0
    ? Math.round((video.progress_frames / video.total_frames) * 100)
    : 0;

  const totalCount = video.result
    ? Object.values(video.result.counts).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <div className="video-card">
      {/* Header */}
      <div className="video-card-header">
        <div className="video-name" title={video.video_name}>
          🎥 {video.video_name}
        </div>
        <span className={`status-badge ${statusClass}`}>
          {video.status}
        </span>
      </div>

      {/* Body */}
      <div className="video-card-body">
        {/* Line status */}
        {isPending && (
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            {hasLine ? (
              <span style={{ color: 'var(--accent-green)' }}>
                ✅ Line set — Ready to process
              </span>
            ) : (
              <span style={{ color: 'var(--accent-amber)' }}>
                ⚠️ Draw counting line to continue
              </span>
            )}
          </div>
        )}

        {/* Processing progress */}
        {isProcessing && (
          <div className="progress-container">
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="progress-text">
              Processing... {progressPercent}% ({video.progress_frames}/{video.total_frames} frames)
            </div>
          </div>
        )}

        {/* Error */}
        {isFailed && video.error && (
          <div className="error-msg">❌ {video.error}</div>
        )}

        {/* Results */}
        {isCompleted && video.result && (
          <>
            <table className="results-table">
              <thead>
                <tr>
                  <th>Vehicle Type</th>
                  <th style={{ textAlign: 'right' }}>Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(video.result.counts)
                  .filter(([, count]) => count > 0)
                  .map(([type, count]) => (
                    <tr key={type}>
                      <td>{type}</td>
                      <td className="count-value" style={{ textAlign: 'right' }}>{count}</td>
                    </tr>
                  ))}
                <tr className="total-row">
                  <td>Total</td>
                  <td style={{ textAlign: 'right' }}>{totalCount}</td>
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              ⏱ {video.result.processing_time}s • {video.result.fps_processing} FPS
            </div>
          </>
        )}

        {/* Timing */}
        {video.created_at && (
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Created: {new Date(video.created_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="video-card-actions">
        {isPending && !hasLine && (
          <button className="btn btn-primary btn-sm" onClick={onDrawLine}>
            ✏️ Draw Line
          </button>
        )}

        {isPending && hasLine && (
          <>
            <button className="btn btn-primary btn-sm" onClick={onDrawLine}>
              ✏️ Redraw Line
            </button>
            <button
              className="btn btn-success btn-sm"
              onClick={handleProcess}
              disabled={loading}
            >
              {loading ? '⏳' : '▶️'} Process
            </button>
          </>
        )}

        {isCompleted && (
          <>
            <a
              className="btn btn-success btn-sm"
              href={getExcelDownloadUrl(video.job_id)}
              download
            >
              📊 Excel
            </a>
            <a
              className="btn btn-secondary btn-sm"
              href={getCsvDownloadUrl(video.job_id)}
              download
            >
              📄 CSV
            </a>
          </>
        )}

        {!isProcessing && (
          <button className="btn btn-danger btn-sm" onClick={handleDelete}>
            🗑️
          </button>
        )}
      </div>
    </div>
  );
}
