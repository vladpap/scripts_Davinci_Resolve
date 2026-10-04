function ScriptListSkeleton() {
  return (
    <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto" aria-label="Загрузка списка скриптов" role="status">
      <span className="block h-3 w-16 animate-pulse rounded bg-muted" />
      {[0, 1, 2].map((item) => (
        <div className="flex gap-3 rounded-md px-2.5 py-2" key={item}>
          <span className="size-7 animate-pulse rounded-md bg-muted" />
          <span className="min-w-0 flex-1 space-y-2 pt-0.5">
            <span className="block h-3 w-3/4 animate-pulse rounded bg-muted" />
            <span className="block h-2.5 w-full animate-pulse rounded bg-muted/70" />
          </span>
        </div>
      ))}
      <span className="sr-only">Загрузка списка скриптов</span>
    </div>
  )
}

function ScriptPanelSkeleton() {
  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto" aria-label="Загрузка панели скрипта" role="status">
      <header className="border-b border-border px-4 py-5 sm:px-8">
        <div className="h-3 w-16 animate-pulse rounded bg-muted" />
        <div className="mt-3 h-7 w-64 max-w-full animate-pulse rounded bg-muted" />
        <div className="mt-3 h-4 max-w-xl animate-pulse rounded bg-muted/70" />
      </header>
      <div className="flex flex-1 flex-col gap-6 px-4 py-6 sm:px-8">
        <div className="rounded-lg border border-border bg-card/40 p-5">
          <div className="h-4 w-24 animate-pulse rounded bg-muted" />
          <div className="mt-6 grid gap-5 md:grid-cols-2">
            {[0, 1, 2, 3].map((item) => (
              <div key={item}>
                <div className="h-3 w-20 animate-pulse rounded bg-muted" />
                <div className="mt-2 h-9 animate-pulse rounded-md bg-muted/70" />
              </div>
            ))}
          </div>
        </div>
        <div className="min-h-40 flex-1 animate-pulse rounded-lg border border-border bg-card/40" />
      </div>
      <span className="sr-only">Загрузка панели скрипта</span>
    </section>
  )
}

export { ScriptListSkeleton, ScriptPanelSkeleton }
