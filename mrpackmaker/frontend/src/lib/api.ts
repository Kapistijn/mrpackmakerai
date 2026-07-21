import { Project, ProjectListItem, ProjectSettings, ModEntry, AIProgressEvent, CompatibilityReport } from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const detail = typeof error.detail === 'string'
        ? error.detail
        : error.detail?.message || error.message || 'Request failed';
      throw new Error(detail);
    }

    return response.json();
  }

  // Health
  async health() {
    return this.request<{ status: string }>('/health');
  }

  // Settings (all public methods intentionally omit integration secrets)
  async getSettings() {
    return this.request<import('../types').SettingsOverview>('/settings');
  }

  async testAiConnection(): Promise<{ provider: string; reachable: boolean; active_model?: string; detail?: string }> {
    return this.request('/settings/ai/test', { method: 'POST' });
  }

  async getAiModels(): Promise<{ provider: string; models: string[]; selected_model?: string }> {
    return this.request('/settings/ai/models');
  }

  // Projects
  async getProjects(): Promise<ProjectListItem[]> {
    return this.request<ProjectListItem[]>('/projects');
  }

  async getProject(id: number): Promise<Project> {
    return this.request<Project>(`/projects/${id}`);
  }

  async createProject(settings: ProjectSettings): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async updateProject(id: number, data: Partial<Project>): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: number): Promise<void> {
    return this.request<void>(`/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // Mods
  async searchMods(params: {
    q?: string;
    mc: string;
    loader: string;
    category?: string;
    source?: string;
    limit?: number;
  }): Promise<{ results: ModEntry[]; total: number; modrinth_available: boolean; curseforge_available: boolean }> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, value.toString());
      }
    });
    return this.request(`/mods/search?${searchParams.toString()}`);
  }

  async getModDetail(source: string, modId: string, mc: string, loader: string): Promise<ModEntry> {
    return this.request<ModEntry>(`/mods/${source}/${modId}?mc=${mc}&loader=${loader}`);
  }

  // AI Generation
  async startGeneration(projectId: number): Promise<{ status: string; project_id: number }> {
    return this.request<{ status: string; project_id: number }>(`/ai/generate/${projectId}`, {
      method: 'POST',
    });
  }

  async cancelGeneration(projectId: number): Promise<{ cancelled: boolean }> {
    return this.request<{ cancelled: boolean }>(`/ai/generate/${projectId}/cancel`, {
      method: 'POST',
    });
  }

  streamGeneration(projectId: number, onEvent: (event: AIProgressEvent) => void, onComplete: () => void, onError: (error: Error) => void): () => void {
    const eventSource = new EventSource(`${API_BASE}/ai/generate/${projectId}/stream`);

    eventSource.addEventListener('progress', (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
      } catch (err) {
        onError(new Error('Failed to parse event data'));
      }
    });

    eventSource.addEventListener('end', () => {
      eventSource.close();
      onComplete();
    });

    eventSource.onerror = () => {
      // A normal job always sends an explicit `end` event before closing.
      // Anything else is a transport failure worth surfacing to the builder.
      eventSource.close();
      onError(new Error('Generation stream disconnected'));
    };

    return () => {
      eventSource.close();
    };
  }

  // Compatibility
  async checkCompatibility(projectId: number): Promise<CompatibilityReport> {
    return this.request<CompatibilityReport>(`/compatibility/${projectId}`, {
      method: 'POST',
    });
  }

  // Modpack
  async generateModpack(projectId: number): Promise<{ status: string; path: string; filename: string }> {
    return this.request<{ status: string; path: string; filename: string }>(`/modpack/${projectId}/generate`, {
      method: 'POST',
    });
  }

  async downloadModpack(projectId: number): Promise<Blob> {
    const response = await fetch(`${API_BASE}/modpack/${projectId}/download`);
    if (!response.ok) {
      throw new Error('Download failed');
    }
    return response.blob();
  }
}

export const api = new ApiClient();
