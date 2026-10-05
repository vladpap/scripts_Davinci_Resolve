import { ArrowLeft, ExternalLink, FileWarning, LoaderCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { OfflineMedia } from '@/lib/scripts'

interface OfflineMediaListProps {
  items: OfflineMedia[]
  isLoading: boolean
  isRevealingId: string | null
  error: string | null
  onBack: () => void
  onReveal: (media: OfflineMedia) => void
}

function OfflineMediaList({ items, isLoading, isRevealingId, error, onBack, onReveal }: OfflineMediaListProps) {
  const mediaByFolder = items.reduce<Map<string, OfflineMedia[]>>((groups, media) => {
    const group = groups.get(media.folder_path)
    if (group) {
      group.push(media)
    } else {
      groups.set(media.folder_path, [media])
    }
    return groups
  }, new Map())

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-border px-4 py-5 sm:px-8 sm:py-6">
        <Button size="sm" variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-3.5" />
          К скриптам
        </Button>
        <div className="mt-4 flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-red-500/15 text-red-300">
            <FileWarning className="size-4.5" />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">Недоступные медиа</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Выберите элемент, чтобы открыть страницу Media в DaVinci Resolve и перейти в содержащую его папку медиатеки.
            </p>
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col px-4 py-5 sm:px-8 sm:py-6">
        {isLoading ? (
          <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" />
            Загрузка списка медиа…
          </div>
        ) : error ? (
          <p className="rounded-md border border-red-400/25 bg-red-400/10 px-3 py-2 text-sm text-red-300">{error}</p>
        ) : items.length === 0 ? (
          <div className="grid flex-1 place-items-center text-center">
            <div>
              <p className="text-sm font-medium">Недоступные медиа не найдены</p>
              <p className="mt-1 text-sm text-muted-foreground">Вероятно, файлы уже доступны или список был обновлён.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {[...mediaByFolder].map(([folderPath, mediaItems]) => (
              <section key={folderPath}>
                <h2 className="mb-2 truncate text-sm font-semibold" title={folderPath}>{folderPath}</h2>
                <ul className="overflow-hidden rounded-lg border border-border bg-card">
                  {mediaItems.map((media) => {
                    const isRevealing = media.id === isRevealingId
                    return (
                      <li className="border-b border-border last:border-b-0" key={media.id}>
                        <button
                          className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:cursor-wait disabled:opacity-60"
                          disabled={isRevealingId !== null}
                          type="button"
                          onClick={() => onReveal(media)}
                        >
                          {isRevealing ? <LoaderCircle className="size-4 shrink-0 animate-spin text-primary" /> : <FileWarning className="size-4 shrink-0 text-red-300" />}
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">{media.name}</span>
                            <span className="mt-1 block truncate text-xs text-muted-foreground" title={media.file_path}>{media.file_path}</span>
                          </span>
                          <ExternalLink className="size-4 shrink-0 text-muted-foreground" />
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export { OfflineMediaList }
