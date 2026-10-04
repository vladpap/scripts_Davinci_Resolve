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
