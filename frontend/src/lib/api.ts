import type { ResolveHealth, ScriptDefinition } from '@/lib/scripts'

export interface ScriptRun {
  run_id: string
  status: 'queued' | 'running' | 'success' | 'error' | 'cancelled'
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail =
      typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : `Ошибка запроса: ${response.status}`
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function fetchHealth(): Promise<ResolveHealth> {
  return request<ResolveHealth>('/api/health')
}

export function fetchScripts(): Promise<ScriptDefinition[]> {
  return request<ScriptDefinition[]>('/api/scripts')
}

export function runScript(scriptId: string, params: Record<string, unknown>): Promise<ScriptRun> {
  return request<ScriptRun>(`/api/scripts/${encodeURIComponent(scriptId)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  })
}

export function stopRun(runId: string): Promise<ScriptRun> {
  return request<ScriptRun>(`/api/runs/${encodeURIComponent(runId)}/stop`, {
    method: 'POST',
  })
}
