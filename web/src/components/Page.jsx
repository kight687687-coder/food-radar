import { useNavigate } from 'react-router-dom'

export function Page({ title, subtitle, back = false, action, children, className = '' }) {
  const navigate = useNavigate()
  return (
    <div className={`page ${className}`}>
      {(title || subtitle || back || action) && (
        <header className="page-header">
          {back && (
            <button className="icon-button back-button" type="button" onClick={() => navigate(-1)} aria-label="返回">
              <span aria-hidden="true">返回</span>
            </button>
          )}
          <div className="page-heading">
            {title && <h1>{title}</h1>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action && <div className="page-header-action">{action}</div>}
        </header>
      )}
      {children}
    </div>
  )
}

export function Section({ title, subtitle, action, children, className = '' }) {
  return (
    <section className={`section ${className}`}>
      {(title || action) && (
        <div className="section-header">
          <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function Card({ children, className = '', as: Element = 'div', ...props }) {
  return <Element className={`card ${className}`} {...props}>{children}</Element>
}
