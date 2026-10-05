import { CheckCircle2, FileSliders, LoaderCircle, Play, RotateCcw, Square, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { EdlRenameForm } from '@/components/EdlRenameForm'
import { ParamForm } from '@/components/ParamForm'
import { runScript, stopRun } from '@/lib/api'
import type { ParameterValue, ScriptDefinition } from '@/lib/scripts'
import { useToast } from '@/lib/toast'

interface ScriptPanelProps {
  script: ScriptDefinition
}

interface RunEvent {
  type: 'status' | 'log' | 'result'
  status?: 'queued' | 'running' | 'success' | 'error' | 'cancelled'
  level?: 'info' | 'warning' | 'error'
  message?: string
  result?: string
}

interface LogEntry {
  level: 'info' | 'warning' | 'error'
  message: string
}

function ScriptPanel({ script }: ScriptPanelProps) {
  const [values, setValues] = useState<Record<string, ParameterValue>>(() => defaultValues(script))
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [runId, setRunId] = useState<string | null>(null)
  const [runStatus, setRunStatus] = useState<RunEvent['status']>('queued')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isFormReady, setIsFormReady] = useState(script.id !== 'edl_to_clip_name')
  const { toast } = useToast()
  const isActiveRun = runId !== null && (runStatus === 'queued' || runStatus === 'running')

  useEffect(() => {
    if (runId === null) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/logs/${runId}`)

    socket.onmessage = (messageEvent) => {
      const event = JSON.parse(messageEvent.data) as RunEvent
      if (event.type === 'status' && event.status) {
        setRunStatus(event.status)
      }
      if (event.type === 'log' && event.message) {
        const entry: LogEntry = { level: event.level ?? 'info', message: event.message }
        setLogs((currentLogs) => [...currentLogs, entry])
      }
      if (event.type === 'result' && event.result) {
        setLogs((currentLogs) => [...currentLogs, { level: 'info', message: `Результат: ${event.result}` }])
      }
    }
    socket.onerror = () => {
      setError('Соединение с потоком логов было потеряно.')
      toast({ title: 'Поток логов недоступен', description: 'Проверьте подключение к backend.', variant: 'error' })
    }

    return () => {
      socket.close()
    }
  }, [runId, toast])

  const resetForm = () => {
    setValues(defaultValues(script))
    setIsFormReady(script.id !== 'edl_to_clip_name')
    setMessage(null)
    setError(null)
  }

  const updateValue = (name: string, value: ParameterValue) => {
    setValues((currentValues) => ({ ...currentValues, [name]: value }))
  }

  const handleRun = async () => {
    setIsSubmitting(true)
    setMessage(null)
    setError(null)
    setLogs([])
    try {
      const run = await runScript(script.id, values)
      setRunId(run.run_id)
      setRunStatus(run.status)
      setMessage(`Скрипт запущен: ${script.name}`)
      toast({ title: 'Скрипт запущен', description: script.name, variant: 'success' })
    } catch (requestError) {
      const description = requestError instanceof Error ? requestError.message : 'Не удалось запустить скрипт.'
      setError(description)
      toast({ title: 'Не удалось запустить скрипт', description, variant: 'error' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStop = async () => {
    if (runId === null) {
      return
    }
    setIsStopping(true)
    setError(null)
    try {
      const run = await stopRun(runId)
      setRunStatus(run.status)
      setMessage(run.status === 'cancelled' ? 'Ожидавший запуск отменён.' : `Статус: ${run.status}`)
      toast({ title: run.status === 'cancelled' ? 'Запуск отменён' : 'Статус запуска изменён', variant: 'info' })
    } catch (requestError) {
      const description = requestError instanceof Error ? requestError.message : 'Не удалось остановить скрипт.'
      setError(description)
      toast({ title: 'Не удалось остановить скрипт', description, variant: 'error' })
    } finally {
      setIsStopping(false)
    }
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-border px-4 py-5 sm:px-8 sm:py-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <FileSliders className="size-3.5" />
            Скрипт
          </div>
          <h1 className="mt-2 text-xl font-semibold tracking-tight sm:text-2xl">{script.name}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{script.description}</p>
        </div>
      </header>

      <div className="flex flex-1 flex-col px-4 py-5 sm:px-8 sm:py-6">
        <div className="rounded-lg border border-border bg-card/40 p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-2">
            <FileSliders className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Параметры</h2>
          </div>
          {script.id === 'edl_to_clip_name' ? (
            <EdlRenameForm disabled={isActiveRun || isSubmitting} values={values} onChange={updateValue} onReadyChange={setIsFormReady} />
          ) : (
            <ParamForm disabled={isActiveRun || isSubmitting} params={script.params} values={values} onChange={updateValue} />
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button className="w-full sm:w-auto" size="sm" variant="outline" disabled={isActiveRun || isSubmitting} onClick={resetForm}>
            <RotateCcw className="size-3.5" />
            Сбросить
          </Button>
          {isActiveRun ? (
            <Button className="w-full sm:w-auto" size="sm" variant="outline" disabled={isStopping} onClick={() => void handleStop()}>
              {isStopping ? <LoaderCircle className="size-3.5 animate-spin" /> : <Square className="size-3.5" />}
              Остановить
            </Button>
          ) : (
            <Button className="w-full sm:w-auto" size="sm" disabled={isSubmitting || !isFormReady} onClick={() => void handleRun()}>
              {isSubmitting ? <LoaderCircle className="size-3.5 animate-spin" /> : <Play className="size-3.5" />}
            Запустить
            </Button>
          )}
        </div>

        {message && (
          <p className="mt-4 flex items-center gap-2 rounded-md border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-300">
            <CheckCircle2 className="size-4" />
            {message}
          </p>
        )}
        {error && (
          <p className="mt-4 flex items-center gap-2 rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm text-red-300">
            <TriangleAlert className="size-4 shrink-0" />
            {error}
          </p>
        )}

        <div className="mt-6 flex min-h-40 flex-1 flex-col rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-medium">Логи выполнения</span>
            <Button size="sm" variant="ghost" disabled={logs.length === 0} onClick={() => setLogs([])}>
              <Square className="size-3.5" />
              Очистить
            </Button>
          </div>
          <div className="min-h-36 max-h-80 flex-1 overflow-auto px-4 py-3 font-mono text-xs leading-5 lg:max-h-none">
            {logs.length === 0 ? (
              <p className="py-5 text-center text-muted-foreground">Ожидание запуска скрипта…</p>
            ) : (
              logs.map((entry, index) => (
                <p className={logClassName(entry.level)} key={`${index}-${entry.message}`}>
                  {entry.message}
                </p>
              ))
            )}
          </div>
        </div>
      </div>

      <footer className="border-t border-border px-4 py-3 text-xs text-muted-foreground sm:px-8">
        {runId ? `Запуск ${runId.slice(0, 8)}: ${statusLabel(runStatus)}` : 'Запуск выполняется в отдельном рабочем потоке'}
      </footer>
    </section>
  )
}

function defaultValues(script: ScriptDefinition): Record<string, ParameterValue> {
  return Object.fromEntries(script.params.map((parameter) => [parameter.name, parameter.default]))
}

function logClassName(level: LogEntry['level']): string {
  if (level === 'error') {
    return 'whitespace-pre-wrap text-red-300'
  }
  if (level === 'warning') {
    return 'whitespace-pre-wrap text-amber-300'
  }
  return 'whitespace-pre-wrap text-muted-foreground'
}

function statusLabel(status: RunEvent['status']): string {
  const labels = {
    queued: 'в очереди',
    running: 'выполняется',
    success: 'успешно завершён',
    error: 'завершён с ошибкой',
    cancelled: 'отменён',
  }
  return status ? labels[status] : 'неизвестный статус'
}

export { ScriptPanel }
