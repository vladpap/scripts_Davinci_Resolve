import { LayoutPanelTop, LoaderCircle, PanelLeftClose, RefreshCw, TerminalSquare } from 'lucide-react'

import { ScriptList } from '@/components/ScriptList'
import { Button } from '@/components/ui/button'
import type { ResolveHealth, ScriptDefinition } from '@/lib/scripts'

interface SidebarProps {
  scripts: ScriptDefinition[]
  selectedScriptId: string
  onSelectScript: (scriptId: string) => void
  health: ResolveHealth | null
  isLoading: boolean
  onRefresh: () => void
  isShowcaseOpen: boolean
  onShowcaseOpen: () => void
}

function Sidebar({ scripts, selectedScriptId, onSelectScript, health, isLoading, onRefresh, isShowcaseOpen, onShowcaseOpen }: SidebarProps) {
  return (
    <aside className="flex flex-col border-b border-border bg-card lg:h-screen lg:min-h-0 lg:overflow-hidden lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <TerminalSquare className="size-4" />
          </span>
          <div>
            <p className="text-sm font-semibold leading-none">Resolve Panel</p>
            <p className="mt-1 text-[11px] text-muted-foreground">Локальная панель</p>
          </div>
        </div>
        <Button aria-label="Свернуть панель" className="hidden lg:inline-flex" size="icon" variant="ghost" disabled>
          <PanelLeftClose className="size-4" />
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col px-3 py-3 lg:py-4">
        <ScriptList isLoading={isLoading} scripts={scripts} selectedScriptId={selectedScriptId} onSelect={onSelectScript} />
        <Button className="mt-3 w-full justify-start" size="sm" variant={isShowcaseOpen ? 'outline' : 'ghost'} onClick={onShowcaseOpen}>
          <LayoutPanelTop className="size-3.5" />
          Примеры UI
        </Button>
      </div>

      <div className="border-t border-border p-3 lg:mt-auto">
        <div className="flex items-center justify-between rounded-md bg-muted/40 px-3 py-2.5">
          <span className="text-xs text-muted-foreground">DaVinci Resolve</span>
          <span
            className={
              isLoading
                ? 'inline-flex items-center gap-1.5 rounded-sm border border-border bg-muted px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-muted-foreground'
                : health?.resolve_connected
                  ? 'inline-flex items-center gap-1.5 rounded-sm border border-emerald-500/30 bg-emerald-500/15 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-400'
                  : 'inline-flex items-center gap-1.5 rounded-sm border border-red-500/30 bg-red-500/15 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-red-400'
            }
          >
            <span
              className={
                isLoading
                  ? 'size-1.5 rounded-full bg-muted-foreground'
                  : health?.resolve_connected
                    ? 'size-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgb(52_211_153)]'
                    : 'size-1.5 rounded-full bg-red-400 shadow-[0_0_6px_rgb(248_113_113)]'
              }
            />
            {isLoading ? 'Загрузка' : health?.resolve_connected ? `Подключен ${health.version}` : 'Не подключен'}
          </span>
        </div>
        <Button className="mt-2 w-full" size="sm" variant="ghost" disabled={isLoading} onClick={onRefresh}>
          {isLoading ? <LoaderCircle className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
          Обновить
        </Button>
      </div>
    </aside>
  )
}

export { Sidebar }
