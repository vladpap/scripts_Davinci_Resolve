import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'
import { type ReactNode, useCallback, useMemo, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { ToastContext, type ToastOptions, type ToastVariant } from '@/lib/toast'
import { cn } from '@/lib/utils'

interface ToastItem {
  id: number
  title: string
  description?: string
  variant: ToastVariant
}

function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const nextId = useRef(0)

  const dismiss = useCallback((id: number) => {
    setToasts((currentToasts) => currentToasts.filter((item) => item.id !== id))
  }, [])

  const toast = useCallback(
    ({ title, description, variant = 'info' }: ToastOptions) => {
      const id = nextId.current
      nextId.current += 1
      setToasts((currentToasts) => [...currentToasts.slice(-3), { id, title, description, variant }])
      window.setTimeout(() => dismiss(id), 5_000)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-end gap-2 sm:left-auto sm:w-96">
        {toasts.map((item) => (
          <Toast key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function Toast({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  const Icon = item.variant === 'success' ? CheckCircle2 : item.variant === 'error' ? TriangleAlert : Info
  const iconClassName = item.variant === 'success' ? 'text-emerald-400' : item.variant === 'error' ? 'text-red-400' : 'text-primary'

  return (
    <div className="toast-enter pointer-events-auto flex w-full items-start gap-3 rounded-lg border border-border bg-card p-3 shadow-2xl shadow-black/30">
      <Icon className={cn('mt-0.5 size-4 shrink-0', iconClassName)} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{item.title}</p>
        {item.description && <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{item.description}</p>}
      </div>
      <Button aria-label="Закрыть уведомление" className="-mr-1 -mt-1 shrink-0" size="icon" variant="ghost" onClick={() => onDismiss(item.id)}>
        <X className="size-3.5" />
      </Button>
    </div>
  )
}

export { ToastProvider }
