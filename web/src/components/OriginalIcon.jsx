export function OriginalIcon({ name, className = '', label }) {
  const classes = `iconfont icon-${name} ${className}`.trim()
  return <span className={classes} aria-hidden={label ? undefined : 'true'} aria-label={label} />
}
