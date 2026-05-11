import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 min timeout for large uploads
});

// ── Video Operations ──

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function getVideos() {
  const res = await api.get('/videos');
  return res.data.videos;
}

export async function getVideoStatus(jobId) {
  const res = await api.get(`/videos/${jobId}`);
  return res.data;
}

export async function getFirstFrame(jobId) {
  const res = await api.get(`/videos/${jobId}/frame`, {
    responseType: 'blob',
  });
  return URL.createObjectURL(res.data);
}

export async function setCountingLine(jobId, x1, y1, x2, y2) {
  const res = await api.post(`/videos/${jobId}/line`, { x1, y1, x2, y2 });
  return res.data;
}

export async function startProcessing(jobId) {
  const res = await api.post(`/videos/${jobId}/process`);
  return res.data;
}

export async function deleteVideo(jobId) {
  const res = await api.delete(`/videos/${jobId}`);
  return res.data;
}

export async function getVideoInfo(jobId) {
  const res = await api.get(`/videos/${jobId}/info`);
  return res.data;
}

// ── Export ──

export function getExcelDownloadUrl(jobId) {
  return `${API_BASE}/videos/${jobId}/export/excel`;
}

export function getCsvDownloadUrl(jobId) {
  return `${API_BASE}/videos/${jobId}/export/csv`;
}

// ── System ──

export async function getSystemInfo() {
  const res = await api.get('/system/info');
  return res.data;
}

export default api;
