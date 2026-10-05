import type { ProjectDashboard as ProjectDashboardData } from '@/lib/scripts'

interface ProjectDashboardProps {
  dashboard: ProjectDashboardData | null
  isLoading: boolean
  onOfflineMediaClick: () => void
}

function ProjectDashboard({ dashboard, isLoading, onOfflineMediaClick }: ProjectDashboardProps) {
  const isConnected = dashboard?.resolve_connected ?? false
  const projectName = isConnected ? dashboard?.project_name || 'Проект не открыт' : 'Resolve не подключён'
  const timelineName = isConnected ? dashboard?.timeline_name || 'Таймлиния не выбрана' : '—'

  return (
    <section aria-label="Сводка активного проекта">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <DashboardCell alert={!isConnected} label="Активный проект" loading={isLoading} value={projectName} />
        <DashboardCell label="Медиа" loading={isLoading} value={isConnected ? String(dashboard?.media_count ?? 0) : '—'} detail={isConnected ? 'элементов в проекте' : undefined} />
        <DashboardCell label="Активная таймлиния" loading={isLoading} value={timelineName} detail={isConnected ? formatTimelineCount(dashboard?.timeline_count ?? 0) : undefined} />
        <DashboardCell alert={(dashboard?.missing_clip_count ?? 0) > 0} clickable={isConnected && (dashboard?.missing_clip_count ?? 0) > 0} detail={isConnected ? 'клипов недоступно' : undefined} label="Оффлайн" loading={isLoading} value={isConnected ? String(dashboard?.missing_clip_count ?? 0) : '—'} onClick={onOfflineMediaClick} />
      </div>
    </section>
  )
}

interface DashboardCellProps {
  label: string
  value: string
  detail?: string
  loading: boolean
  alert?: boolean
  clickable?: boolean
  onClick?: () => void
}

function DashboardCell({ label, value, detail, loading, alert = false, clickable = false, onClick }: DashboardCellProps) {
  const className = alert
    ? 'min-w-0 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-4'
    : 'min-w-0 rounded-lg border border-border bg-card/40 px-4 py-4'
  const content = <>
    <p className={alert ? 'text-[11px] font-semibold uppercase tracking-[0.08em] text-red-200/80' : 'text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground'}>{label}</p>
    {loading ? (
      <span className="mt-3 block h-5 w-3/4 animate-pulse rounded bg-muted" />
    ) : (
      <p className={alert ? 'mt-2 truncate text-lg font-semibold text-red-300' : 'mt-2 truncate text-lg font-semibold'} title={value}>{value}</p>
    )}
    {detail && !loading && <p className={alert ? 'mt-1 text-xs text-red-200/80' : 'mt-1 text-xs text-muted-foreground'}>{detail}</p>}
  </>

  if (clickable && onClick) {
    return <button aria-label="Открыть список недоступных медиа" className={`${className} cursor-pointer text-left transition-colors hover:border-red-400/70 hover:bg-red-500/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`} type="button" onClick={onClick}>{content}</button>
  }

  return (
    <div className={className}>{content}</div>
  )
}

function formatTimelineCount(count: number): string {
  const remainder = count % 100
  if (remainder >= 11 && remainder <= 14) {
    return `${count} таймлайнов в проекте`
  }
  if (count % 10 === 1) {
    return `${count} таймлайн в проекте`
  }
  if (count % 10 >= 2 && count % 10 <= 4) {
    return `${count} таймлайна в проекте`
  }
  return `${count} таймлайнов в проекте`
}

export { ProjectDashboard }
