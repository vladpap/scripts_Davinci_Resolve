import { Check, ChevronDown, Copy, FileText, Info, LoaderCircle, Plus, Search, SlidersHorizontal, TerminalSquare, Trash2 } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/lib/toast'

function UiShowcase() {
  const [isEnabled, setIsEnabled] = useState(true)
  const [environment, setEnvironment] = useState('Рабочее')
  const [notes, setNotes] = useState('Экспортировать маркеры в JSON после проверки таймлайна.')
  const [progress, setProgress] = useState(64)
  const { toast } = useToast()

  return (
    <section className="min-h-0 min-w-0 overflow-y-auto">
      <header className="border-b border-border px-4 py-5 sm:px-8 sm:py-6">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
            <SlidersHorizontal className="size-4.5" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">Элементы интерфейса</p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">Примеры элементов интерфейса</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Интерактивная витрина базовых элементов веб-панели. Здесь можно сверить состояния и поведение перед использованием в новых экранах.
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 p-4 sm:p-8 lg:grid-cols-2">
        <ShowcaseCard description="Основные действия и варианты состояний." title="Кнопки">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => toast({ title: 'Действие выполнено', description: 'Пример основной кнопки.', variant: 'success' })}><Plus className="size-4" />Создать</Button>
            <Button variant="outline"><Copy className="size-4" />Копировать</Button>
            <Button variant="ghost"><FileText className="size-4" />Подробнее</Button>
            <Button disabled><LoaderCircle className="size-4 animate-spin" />Загрузка</Button>
            <Button aria-label="Поиск" size="icon" variant="outline" onClick={() => toast({ title: 'Поиск выполнен', description: 'Пример основной кнопки.', variant: 'success' })}><Search className="size-4" /></Button>
          </div>
        </ShowcaseCard>

        <ShowcaseCard description="Статусы, подсказки и индикаторы процесса." title="Статусы">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge color="bg-emerald-400" label="Готово" tone="border-emerald-500/30 bg-emerald-500/15 text-emerald-400" />
            <StatusBadge color="bg-amber-400" label="В очереди" tone="border-amber-500/30 bg-amber-500/15 text-amber-400" />
            <StatusBadge color="bg-red-400" label="Ошибка" tone="border-red-500/30 bg-red-500/15 text-red-400" />
          </div>
          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground"><span>Выполнение</span><span>{progress}%</span></div>
            <div aria-label={`Выполнение: ${progress}%`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={progress} className="h-2 overflow-hidden rounded-full bg-muted" role="progressbar">
              <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${progress}%` }} />
            </div>
            <input aria-label="Прогресс" className="mt-3 w-full accent-[var(--primary)]" max="100" min="0" type="range" value={progress} onChange={(event) => setProgress(Number(event.target.value))} />
          </div>
        </ShowcaseCard>

        <ShowcaseCard description="Поля для настройки скрипта и ввода данных." title="Поля ввода">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Название задачи">
              <input className={inputClassName} defaultValue="Экспорт таймлайна" placeholder="Введите название" />
            </Field>
            <Field label="Окружение">
              <div className="relative">
                <select className={inputClassName} value={environment} onChange={(event) => setEnvironment(event.target.value)}>
                  <option>Рабочее</option>
                  <option>Тестовое</option>
                  <option>Разработка</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-2.5 size-4 text-muted-foreground" />
              </div>
            </Field>
            <Field className="sm:col-span-2" label="Описание">
              <textarea className="min-h-24 w-full rounded-md border border-input bg-muted/30 px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring" value={notes} onChange={(event) => setNotes(event.target.value)} />
            </Field>
          </div>
        </ShowcaseCard>

        <ShowcaseCard description="Переключатели для включения параметров и выбора вариантов." title="Флажки и переключатели">
          <label className="flex cursor-pointer items-center justify-between rounded-md border border-border bg-muted/20 px-3 py-3">
            <span><span className="block text-sm font-medium">Добавить маркеры</span><span className="mt-0.5 block text-xs text-muted-foreground">Создавать маркеры в текущем таймлайне</span></span>
            <input checked={isEnabled} className="size-4 accent-[var(--primary)]" type="checkbox" onChange={(event) => setIsEnabled(event.target.checked)} />
          </label>
          <fieldset className="mt-4">
            <legend className="text-sm font-medium">Формат экспорта</legend>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
              {['JSON', 'CSV', 'EDL'].map((format, index) => (
                <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground" key={format}>
                  <input className="size-4 accent-[var(--primary)]" defaultChecked={index === 0} name="format" type="radio" />{format}
                </label>
              ))}
            </div>
          </fieldset>
        </ShowcaseCard>

        <ShowcaseCard description="Типичные сообщения и список операций." title="Сообщения и списки">
          <div className="flex gap-3 rounded-md border border-primary/25 bg-primary/10 p-3 text-sm">
            <Info className="mt-0.5 size-4 shrink-0 text-primary" />
            <p className="leading-5 text-muted-foreground">Подсказка: параметры сохраняются только на время текущей сессии.</p>
          </div>
          <ul className="mt-4 divide-y divide-border rounded-md border border-border">
            {['Проверить подключение к Resolve', 'Собрать список клипов', 'Создать файл экспорта'].map((item, index) => (
              <li className="flex items-center gap-3 px-3 py-2.5 text-sm" key={item}>
                <span className="flex size-5 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400"><Check className="size-3" /></span>
                <span className="flex-1">{item}</span>
                <span className="text-xs text-muted-foreground">{index + 1}</span>
              </li>
            ))}
          </ul>
        </ShowcaseCard>

        <ShowcaseCard description="Пустое состояние и необратимое действие." title="Пустое состояние">
          <div className="grid place-items-center rounded-md border border-dashed border-border bg-muted/15 px-4 py-6 text-center">
            <span className="flex size-9 items-center justify-center rounded-md bg-muted text-muted-foreground"><TerminalSquare className="size-4" /></span>
            <p className="mt-3 text-sm font-medium">Данные пока отсутствуют</p>
            <p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">Запустите скрипт, чтобы увидеть историю операций.</p>
            <Button className="mt-4 text-red-400 hover:bg-red-500/10 hover:text-red-300" size="sm" variant="ghost"><Trash2 className="size-3.5" />Очистить историю</Button>
          </div>
        </ShowcaseCard>
      </div>
    </section>
  )
}

const inputClassName = 'h-9 w-full appearance-none rounded-md border border-input bg-muted/30 px-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring'

function ShowcaseCard({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <Card><CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader><CardContent>{children}</CardContent></Card>
}

function Field({ label, className, children }: { label: string; className?: string; children: React.ReactNode }) {
  return <div className={className}><label className="text-sm font-medium">{label}</label><div className="mt-2">{children}</div></div>
}

function StatusBadge({ label, tone, color }: { label: string; tone: string; color: string }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${tone}`}><span className={`size-1.5 rounded-full ${color}`} />{label}</span>
}

export { UiShowcase }
