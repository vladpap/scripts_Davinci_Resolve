import { FolderX, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'

import { ScriptPanelSkeleton } from '@/components/LoadingSkeleton'
import { ScriptPanel } from '@/components/ScriptPanel'
import { Sidebar } from '@/components/Sidebar'
import { UiShowcase } from '@/components/UiShowcase'
import { Button } from '@/components/ui/button'
import { fetchHealth, fetchScripts } from '@/lib/api'
import type { ResolveHealth, ScriptDefinition } from '@/lib/scripts'
import { useToast } from '@/lib/toast'

function App() {
  const [scripts, setScripts] = useState<ScriptDefinition[]>([])
  const [health, setHealth] = useState<ResolveHealth | null>(null)
  const [selectedScriptId, setSelectedScriptId] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<'scripts' | 'showcase'>('scripts')
  const { toast } = useToast()

  const applyPanelData = (nextHealth: ResolveHealth, nextScripts: ScriptDefinition[]) => {
    setHealth(nextHealth)
    setScripts(nextScripts)
    setSelectedScriptId((currentId) => nextScripts.some((script) => script.id === currentId) ? currentId : (nextScripts[0]?.id ?? ''))
  }

  const refresh = async (notify = true) => {
    setIsLoading(true)
    setError(null)
    try {
      const [nextHealth, nextScripts] = await Promise.all([fetchHealth(), fetchScripts()])
      applyPanelData(nextHealth, nextScripts)
      if (notify) {
        toast({ title: 'Панель обновлена', description: `Скриптов загружено: ${nextScripts.length}.`, variant: 'success' })
      }
    } catch (requestError) {
      const description = requestError instanceof Error ? requestError.message : 'Не удалось загрузить данные панели.'
      setError(description)
      if (notify) {
        toast({ title: 'Не удалось обновить панель', description, variant: 'error' })
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let isCurrent = true

    void Promise.all([fetchHealth(), fetchScripts()])
      .then(([nextHealth, nextScripts]) => {
        if (isCurrent) {
          applyPanelData(nextHealth, nextScripts)
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrent) {
          setError(requestError instanceof Error ? requestError.message : 'Не удалось загрузить данные панели.')
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false)
        }
      })

    return () => {
      isCurrent = false
    }
  }, [])

  const selectedScript = scripts.find((script) => script.id === selectedScriptId)

  return (
    <main className="min-h-screen bg-background text-foreground lg:h-screen lg:min-h-0 lg:overflow-hidden lg:grid lg:grid-cols-[19rem_minmax(0,1fr)]">
      <Sidebar health={health} isLoading={isLoading} isShowcaseOpen={view === 'showcase'} scripts={scripts} selectedScriptId={selectedScriptId} onRefresh={() => void refresh()} onSelectScript={(scriptId) => { setSelectedScriptId(scriptId); setView('scripts') }} onShowcaseOpen={() => setView('showcase')} />
      {view === 'showcase' ? (
        <UiShowcase />
      ) : isLoading ? (
        <ScriptPanelSkeleton />
      ) : selectedScript ? (
        <ScriptPanel key={selectedScript.id} script={selectedScript} />
      ) : (
        <section className="grid min-h-72 place-items-center px-4 py-10 text-center sm:px-6">
          <div>
            <span className="mx-auto flex size-10 items-center justify-center rounded-lg border border-border bg-muted/50 text-muted-foreground">
              <FolderX className="size-5" />
            </span>
            <h1 className="mt-4 text-lg font-semibold">Скрипты не загружены</h1>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{error ?? 'Добавьте валидный Python-скрипт в backend/scripts и перезапустите сервер.'}</p>
            {error && <Button className="mt-5" size="sm" variant="outline" onClick={() => void refresh()}><RefreshCw className="size-3.5" />Повторить</Button>}
          </div>
        </section>
      )}
    </main>
  )
}

export default App
