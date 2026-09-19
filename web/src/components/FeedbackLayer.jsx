import { useEffect } from 'react'
import { useApp } from '../context/AppContext'
import { OriginalIcon } from './OriginalIcon'

export function FeedbackLayer() {
  const { toast, dialog, settleDialog } = useApp()

  return (
    <>
      {toast && <Toast key={toast.id} toast={toast} />}
      {dialog && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => settleDialog(false)}>
          <section className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="dialog-title" onMouseDown={event => event.stopPropagation()}>
            <h2 id="dialog-title">{dialog.title}</h2>
            <p>{dialog.message}</p>
            <div className="dialog-actions">
              <button className="button secondary" type="button" onClick={() => settleDialog(false)}>取消</button>
              <button className={`button ${dialog.danger ? 'danger' : 'primary'}`} type="button" onClick={() => settleDialog(true)}>{dialog.confirmLabel}</button>
            </div>
          </section>
        </div>
      )}
    </>
  )
}

function Toast({ toast }) {
  const { dismissToast } = useApp()
  const icon = toast.tone === 'success' ? 'shield-check' : toast.tone === 'neutral' ? 'ai' : 'shield-warning'

  useEffect(() => {
    const timer = setTimeout(() => {
      dismissToast()
    }, 2800)
    return () => clearTimeout(timer)
  }, [dismissToast, toast.id])

  return (
    <div className={`toast toast-${toast.tone}`} role="status" data-toast-id={toast.id}>
      <OriginalIcon name={icon} />
      <span>{toast.message}</span>
    </div>
  )
}
