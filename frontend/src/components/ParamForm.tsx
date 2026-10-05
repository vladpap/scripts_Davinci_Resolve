import type { ChangeEvent } from 'react'

import type { ParameterValue, ScriptParameter } from '@/lib/scripts'

interface ParamFormProps {
  params: ScriptParameter[]
  values: Record<string, ParameterValue>
  disabled: boolean
  onChange: (name: string, value: ParameterValue) => void
}

function ParamForm({ params, values, disabled, onChange }: ParamFormProps) {
  if (params.length === 0) {
    return <p className="text-sm text-muted-foreground">У этого скрипта нет настраиваемых параметров.</p>
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      {params.map((parameter) => (
        <ParameterField
          disabled={disabled}
          key={parameter.name}
          parameter={parameter}
          value={values[parameter.name] ?? parameter.default}
          onChange={onChange}
        />
      ))}
    </div>
  )
}

interface ParameterFieldProps {
  parameter: ScriptParameter
  value: ParameterValue
  disabled: boolean
  onChange: (name: string, value: ParameterValue) => void
}

function ParameterField({ parameter, value, disabled, onChange }: ParameterFieldProps) {
  const inputClassName =
    'mt-2 h-9 w-full rounded-md border border-input bg-muted/30 px-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50'
  const label = <label className="text-sm font-medium" htmlFor={parameter.name}>{formatLabel(parameter.name)}</label>

  if (parameter.type === 'bool') {
    return (
      <label className="flex items-center justify-between rounded-md border border-border bg-muted/20 px-3 py-3" htmlFor={parameter.name}>
        <span>
          <span className="block text-sm font-medium">{formatLabel(parameter.name)}</span>
          <span className="mt-0.5 block text-xs text-muted-foreground">Включить параметр</span>
        </span>
        <input
          checked={Boolean(value)}
          className="size-4 accent-[var(--primary)]"
          disabled={disabled}
          id={parameter.name}
          type="checkbox"
          onChange={(event) => onChange(parameter.name, event.target.checked)}
        />
      </label>
    )
  }

  if (parameter.type === 'select') {
    return (
      <div>
        {label}
        <select
          className={inputClassName}
          disabled={disabled}
          id={parameter.name}
          value={String(value)}
          onChange={(event) => onChange(parameter.name, event.target.value)}
        >
          {parameter.options?.map((option) => (
            <option key={String(option)} value={String(option)}>{String(option)}</option>
          ))}
        </select>
      </div>
    )
  }

  if (parameter.type === 'textarea') {
    return (
      <div className="md:col-span-2">
        {label}
        <textarea
          className="mt-2 min-h-24 w-full rounded-md border border-input bg-muted/30 px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled}
          id={parameter.name}
          value={String(value)}
          onChange={(event) => onChange(parameter.name, event.target.value)}
        />
      </div>
    )
  }

  return (
    <div>
      {label}
      <input
        className={inputClassName}
        disabled={disabled}
        id={parameter.name}
        min={parameter.type === 'number' ? 0 : undefined}
        placeholder={parameter.type === 'file' ? 'Например: ~/Desktop/export.json' : undefined}
        step={parameter.type === 'number' ? 'any' : undefined}
        type={parameter.type === 'number' ? 'number' : 'text'}
        value={String(value)}
        onChange={(event) => handleTextChange(event, parameter, onChange)}
      />
      {parameter.type === 'file' && (
        <p className="mt-1.5 text-xs text-muted-foreground">Укажите путь на компьютере, где запущена серверная часть.</p>
      )}
    </div>
  )
}

function handleTextChange(
  event: ChangeEvent<HTMLInputElement>,
  parameter: ScriptParameter,
  onChange: (name: string, value: ParameterValue) => void,
) {
  const value = parameter.type === 'number' ? event.target.valueAsNumber : event.target.value
  onChange(parameter.name, Number.isNaN(value) ? 0 : value)
}

function formatLabel(name: string): string {
  return name.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
}

export { ParamForm }
