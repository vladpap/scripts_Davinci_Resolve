import { FileUp } from 'lucide-react'
import { useEffect, useId, useRef, type ChangeEvent } from 'react'

import { Button } from '@/components/ui/button'
import type { ParameterValue } from '@/lib/scripts'

const CLIP_COLORS: Record<string, string> = {
  Orange: '#EB6E01',
  Apricot: '#FFA833',
  Yellow: '#D4AD1F',
  Lime: '#9FC615',
  Olive: '#5F9921',
  Green: '#448F65',
  Teal: '#019899',
  Navy: '#005278',
  Blue: '#4376A1',
  Purple: '#9972A0',
  Violet: '#D0568D',
  Pink: '#E98CB5',
  Tan: '#B9AF97',
  Beige: '#C4A07C',
  Brown: '#996601',
  Chocolate: '#8C5A3F',
}

interface EdlRenameFormProps {
  values: Record<string, ParameterValue>
  disabled: boolean
  onChange: (name: string, value: ParameterValue) => void
  onReadyChange: (isReady: boolean) => void
}

function EdlRenameForm({ values, disabled, onChange, onReadyChange }: EdlRenameFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()
  const hasEdl = typeof values.edl_content === 'string' && values.edl_content.trim().length > 0
  const selectedColor = typeof values.clip_color === 'string' ? values.clip_color : 'Orange'

  useEffect(() => {
    onReadyChange(hasEdl)
  }, [hasEdl, onReadyChange])

  const selectFile = () => fileInputRef.current?.click()

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      onChange('edl_content', typeof reader.result === 'string' ? reader.result : '')
      onChange('edl_filename', file.name)
    }
    reader.onerror = () => {
      onChange('edl_content', '')
      onChange('edl_filename', '')
    }
    reader.readAsText(file)
    event.target.value = ''
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="text-sm font-medium" htmlFor={inputId}>Путь к EDL</label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            className="h-9 min-w-0 flex-1 rounded-md border border-input bg-muted/30 px-3 text-sm text-muted-foreground outline-none"
            id={inputId}
            readOnly
            value={typeof values.edl_filename === 'string' ? values.edl_filename : ''}
            placeholder="Файл не выбран"
          />
          <Button disabled={disabled} size="sm" type="button" variant="outline" onClick={selectFile}>
            <FileUp className="size-3.5" />
            Выбрать .edl
          </Button>
          <input accept=".edl,text/plain" className="sr-only" disabled={disabled} ref={fileInputRef} type="file" onChange={handleFileChange} />
        </div>
        <p className={hasEdl ? 'mt-2 text-xs text-muted-foreground' : 'mt-2 text-xs text-amber-300'}>
          {hasEdl ? 'EDL-файл выбран и готов к проверке.' : '⚠️ Для работы нужно выбрать EDL-файл.'}
        </p>
      </div>

      <Checkbox
        checked={Boolean(values.strict_count_match)}
        disabled={disabled}
        label="Строгая проверка по количеству склеек"
        name="strict_count_match"
        onChange={onChange}
      />

      <div className="rounded-lg border border-border bg-muted/20 p-4">
        <div>
          <h3 className="text-sm font-semibold">Дополнительные метки</h3>
          <p className="mt-1 text-xs text-muted-foreground">Применяются к клипам, успешно сопоставленным с EDL.</p>
        </div>
        <div className="mt-4 flex flex-col gap-3 xl:flex-row xl:flex-wrap xl:items-center">
          <span aria-label={`Выбранный цвет: ${selectedColor}`} className="size-6 shrink-0 rounded-md border border-white/20 shadow-sm" style={{ backgroundColor: CLIP_COLORS[selectedColor] ?? CLIP_COLORS.Orange }} />
          <select
            className="h-9 min-w-40 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled}
            value={selectedColor}
            onChange={(event) => onChange('clip_color', event.target.value)}
          >
            {Object.keys(CLIP_COLORS).map((color) => <option key={color} value={color}>{color}</option>)}
          </select>
          <Checkbox checked={Boolean(values.set_clip_color)} compact disabled={disabled} label="Цвет клипа" name="set_clip_color" onChange={onChange} />
          <Checkbox checked={Boolean(values.add_flag)} compact disabled={disabled} label="Флаг на клипе" name="add_flag" onChange={onChange} />
          <Checkbox checked={Boolean(values.add_marker)} compact disabled={disabled} label="Маркер" name="add_marker" onChange={onChange} />
        </div>
      </div>
    </div>
  )
}

interface CheckboxProps {
  name: string
  label: string
  checked: boolean
  disabled: boolean
  compact?: boolean
  onChange: (name: string, value: ParameterValue) => void
}

function Checkbox({ name, label, checked, disabled, compact = false, onChange }: CheckboxProps) {
  return (
    <label className={compact ? 'flex items-center gap-2 text-sm font-medium' : 'flex items-center gap-3 rounded-md border border-border bg-muted/20 px-3 py-3 text-sm font-medium'} htmlFor={name}>
      <input checked={checked} className="size-4 accent-[var(--primary)]" disabled={disabled} id={name} type="checkbox" onChange={(event) => onChange(name, event.target.checked)} />
      {label}
    </label>
  )
}

export { EdlRenameForm }
