import { FileCode2, Search } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { ScriptDefinition } from '@/lib/scripts'
import { cn } from '@/lib/utils'
import { ScriptListSkeleton } from '@/components/LoadingSkeleton'

interface ScriptListProps {
  scripts: ScriptDefinition[]
  isLoading: boolean
  selectedScriptId: string
  onSelect: (scriptId: string) => void
}

function ScriptList({ scripts, isLoading, selectedScriptId, onSelect }: ScriptListProps) {
  const [query, setQuery] = useState('')
  const filteredScripts = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase()
    if (!normalizedQuery) {
      return scripts
    }
    return scripts.filter((script) =>
      `${script.name} ${script.description}`.toLocaleLowerCase().includes(normalizedQuery),
    )
  }, [query, scripts])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <label className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          aria-label="Поиск скриптов"
          className="h-9 w-full rounded-md border border-input bg-muted/40 pl-9 pr-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
          placeholder="Поиск скриптов"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      {isLoading ? <ScriptListSkeleton /> : <div className="mt-4 min-h-0 flex-1 space-y-1 overflow-y-auto">
        <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Скрипты
        </p>
        {filteredScripts.map((script) => {
          const isSelected = script.id === selectedScriptId

          return (
            <button
              aria-pressed={isSelected}
              className={cn(
                'flex w-full gap-3 rounded-md px-2.5 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isSelected
                  ? 'bg-primary/15 text-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )}
              key={script.id}
              onClick={() => onSelect(script.id)}
              type="button"
            >
              <span
                className={cn(
                  'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border',
                  isSelected
                    ? 'border-primary/40 bg-primary/15 text-primary'
                    : 'border-border bg-muted/60 text-muted-foreground',
                )}
              >
                <FileCode2 className="size-3.5" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{script.name}</span>
                <span className="mt-1 block line-clamp-2 text-xs leading-4 text-muted-foreground">
                  {script.description}
                </span>
              </span>
            </button>
          )
        })}
        {filteredScripts.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">Скрипты не найдены.</p>
        )}
      </div>}
    </div>
  )
}

export { ScriptList }
