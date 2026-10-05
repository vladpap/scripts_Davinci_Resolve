export type ParameterType = 'text' | 'number' | 'select' | 'bool' | 'textarea' | 'file'

export type ParameterValue = string | number | boolean

export interface ScriptParameter {
  name: string
  type: ParameterType
  default: ParameterValue
  options?: ParameterValue[]
}

export interface ScriptDefinition {
  id: string
  name: string
  description: string
  params: ScriptParameter[]
}

export interface ResolveHealth {
  resolve_connected: boolean
  version: string
}

export interface ProjectDashboard {
  resolve_connected: boolean
  project_name: string
  media_count: number
  timeline_name: string
  timeline_count: number
  missing_clip_count: number
}

export interface OfflineMedia {
  id: string
  name: string
  file_path: string
  folder_path: string
}
