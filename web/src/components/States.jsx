import { OriginalIcon } from './OriginalIcon'

export function LoadingState({ label = '正在加载' }) {
  return <div className="state-block"><span className="native-spinner" /><p>{label}</p></div>
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="empty-state">
      <OriginalIcon name="search" className="empty-icon" />
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}

export function LoadingOverlay({ label = '正在分析配料表' }) {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <div className="loading-panel"><span className="native-spinner" /><strong>{label}</strong><span>通常需要 10 到 30 秒</span></div>
    </div>
  )
}
