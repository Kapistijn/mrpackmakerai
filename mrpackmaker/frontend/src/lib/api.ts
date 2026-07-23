import { Project, ProjectListItem, ProjectSettings, ModEntry, AIProgressEvent, CompatibilityReport, SettingsOverview, UnifiedSettingsUpdate, SecretName, ApiTestResult } from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const detail = typeof error.detail === 'string' ? error.detail : error.detail?.message || error.message || 'Request failed';
      throw new Error(detail);
    }
    // DELETE endpoints intentionally return 204 with no JSON body. Calling
    // response.json() here caused the UI to report "Failed to delete project"
    // after the backend had already deleted it successfully.
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T;
    }
    const contentType = response.headers.get('content-type') || '';
    return contentType.includes('application/json') ? response.json() : (await response.text() as T);
  }

  async health() { return this.request<{ status: string }>('/health'); }
  async getSettings() { return this.request<SettingsOverview>('/settings'); }
  async updateSettings(update: UnifiedSettingsUpdate): Promise<SettingsOverview> { return this.request('/settings/config', { method: 'PATCH', body: JSON.stringify(update) }); }
  async deleteSecret(name: SecretName): Promise<SettingsOverview> { return this.request(`/settings/secrets/${name}`, { method: 'DELETE' }); }
  async testAiConnection(): Promise<ApiTestResult> { return this.request('/settings/ai/test', { method: 'POST' }); }
  async testModrinth(): Promise<ApiTestResult> { return this.request('/settings/modrinth/test', { method: 'POST' }); }
  async testCurseforge(): Promise<ApiTestResult> { return this.request('/settings/curseforge/test', { method: 'POST' }); }
  async getAiModels(): Promise<{ provider: string; models: string[]; selected_model?: string }> { return this.request('/settings/ai/models'); }
  async setAiModel(model: string): Promise<SettingsOverview['ai']> { return this.request('/settings/ai/model', { method: 'POST', body: JSON.stringify({ model }) }); }
  async testTts(text?: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/settings/voice/tts/test`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(text ? { text } : {}) });
    if (!response.ok) { const error = await response.json().catch(() => ({ detail: 'TTS test failed' })); throw new Error(typeof error.detail === 'string' ? error.detail : 'TTS test failed'); }
    return response.blob();
  }
  async getProjects(): Promise<ProjectListItem[]> { return this.request<ProjectListItem[]>('/projects'); }
  async getProject(id: number): Promise<Project> { return this.request<Project>(`/projects/${id}`); }
  async createProject(settings: ProjectSettings): Promise<Project> { return this.request<Project>('/projects', { method: 'POST', body: JSON.stringify(settings) }); }
  async updateProject(id: number, data: Partial<Project>): Promise<Project> { return this.request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }); }
  async deleteProject(id: number): Promise<void> { return this.request<void>(`/projects/${id}`, { method: 'DELETE' }); }
  async getLoaderVersions(mc: string, loader: string): Promise<{ versions: Array<{ id: string; version: string; type: string; published?: string }>; loader: string; minecraft_version: string }> { return this.request(`/projects/loader-versions?mc=${encodeURIComponent(mc)}&loader=${encodeURIComponent(loader)}`); }
  async searchMods(params: { q?: string; mc: string; loader: string; category?: string; source?: string; limit?: number }): Promise<{ results: ModEntry[]; total: number; modrinth_available: boolean; curseforge_available: boolean }> { const searchParams = new URLSearchParams(); Object.entries(params).forEach(([key, value]) => { if (value !== undefined) searchParams.append(key, value.toString()); }); return this.request(`/mods/search?${searchParams.toString()}`); }
  async getModDetail(source: string, modId: string, mc: string, loader: string): Promise<ModEntry> { return this.request<ModEntry>(`/mods/${source}/${modId}?mc=${mc}&loader=${loader}`); }
  async startGeneration(projectId: number): Promise<{ status: string; project_id: number; mode?: string }> { return this.request(`/ai/generate/${projectId}`, { method: 'POST' }); }
  async startQuickGeneration(projectId: number): Promise<{ status: string; project_id: number; mode?: string }> { return this.request(`/ai/generate/${projectId}/quick`, { method: 'POST' }); }
  async cancelGeneration(projectId: number): Promise<{ cancelled: boolean }> { return this.request(`/ai/generate/${projectId}/cancel`, { method: 'POST' }); }
  streamGeneration(projectId: number, onEvent: (event: AIProgressEvent) => void, onComplete: () => void, onError: (error: Error) => void): () => void {
    const eventSource = new EventSource(`${API_BASE}/ai/generate/${projectId}/stream`);
    eventSource.addEventListener('progress', (e) => { try { onEvent(JSON.parse(e.data)); } catch { onError(new Error('Failed to parse event data')); } });
    eventSource.addEventListener('end', () => { eventSource.close(); onComplete(); });
    eventSource.onerror = () => { eventSource.close(); onError(new Error('Generation stream disconnected')); };
    return () => eventSource.close();
  }
  async checkCompatibility(projectId: number): Promise<CompatibilityReport> { return this.request(`/compatibility/${projectId}`, { method: 'POST' }); }
  async generateModpack(projectId: number): Promise<{ status: string; path: string; filename: string }> { return this.request(`/modpack/${projectId}/generate`, { method: 'POST' }); }
  async downloadModpack(projectId: number): Promise<Blob> { const response = await fetch(`${API_BASE}/modpack/${projectId}/download`); if (!response.ok) throw new Error('Download failed'); return response.blob(); }
}

export const api = new ApiClient();
