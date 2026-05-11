import { useState, useEffect, useCallback } from 'react';
import { getVideos, getSystemInfo, uploadVideo } from './api';
import VideoUpload from './components/VideoUpload';
import VideoCard from './components/VideoCard';
import LineDrawer from './components/LineDrawer';

export default function App() {
  const [videos, setVideos] = useState([]);
  const [systemInfo, setSystemInfo] = useState(null);
  const [lineDrawerJob, setLineDrawerJob] = useState(null);
  const [error, setError] = useState('');

  // Fetch system info on mount
  useEffect(() => {
    getSystemInfo()
      .then(setSystemInfo)
      .catch(() => setSystemInfo({ has_gpu: false, device: 'cpu', optimal_workers: 1 }));
  }, []);

  // Poll videos every 2 seconds
  const fetchVideos = useCallback(async () => {
    try {
      const data = await getVideos();
      setVideos(data || []);
    } catch {
      // Backend might not be ready yet
    }
  }, []);

  useEffect(() => {
    fetchVideos();
    const interval = setInterval(fetchVideos, 2000);
    return () => clearInterval(interval);
  }, [fetchVideos]);

  const handleUpload = async (file) => {
    try {
      setError('');
      await uploadVideo(file);
      await fetchVideos();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    }
  };

  const handleLineDrawn = () => {
    setLineDrawerJob(null);
    fetchVideos();
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <span className="header-logo">🚦</span>
          <div>
            <h1>Traffic Video Analytics</h1>
            <span className="header-subtitle">Offline Scalable Traffic Counting System</span>
          </div>
        </div>
        <div className="header-system">
          {systemInfo && (
            <>
              <div className={`system-badge ${systemInfo.has_gpu ? 'gpu' : 'cpu'}`}>
                <span className="dot"></span>
                {systemInfo.has_gpu
                  ? `GPU: ${systemInfo.gpu?.name || 'Active'}`
                  : 'CPU Mode'}
              </div>
              <div className="system-badge cpu">
                ⚡ {systemInfo.optimal_workers} Worker{systemInfo.optimal_workers > 1 ? 's' : ''}
              </div>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Upload Section */}
        <section>
          <div className="section-header">
            <h2 className="section-title">📤 Upload Videos</h2>
          </div>
          <VideoUpload onUpload={handleUpload} />
          {error && <div className="error-msg">⚠️ {error}</div>}
        </section>

        {/* Videos Section */}
        <section style={{ marginTop: '2rem' }}>
          <div className="section-header">
            <h2 className="section-title">📋 Video Queue</h2>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              {videos.length} video{videos.length !== 1 ? 's' : ''}
            </span>
          </div>

          {videos.length === 0 ? (
            <div className="empty-state">
              <div className="icon">🎬</div>
              <h3>No videos yet</h3>
              <p>Upload a traffic video to get started</p>
            </div>
          ) : (
            <div className="video-grid">
              {videos.map((video) => (
                <VideoCard
                  key={video.job_id}
                  video={video}
                  onDrawLine={() => setLineDrawerJob(video)}
                  onRefresh={fetchVideos}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      {/* Line Drawing Modal */}
      {lineDrawerJob && (
        <LineDrawer
          jobId={lineDrawerJob.job_id}
          videoName={lineDrawerJob.video_name}
          onDone={handleLineDrawn}
          onCancel={() => setLineDrawerJob(null)}
        />
      )}
    </div>
  );
}
