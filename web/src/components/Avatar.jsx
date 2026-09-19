export function Avatar({ src, name = '我', className = '' }) {
  return (
    <span className={`avatar ${className}`}>
      {src ? <img src={src} alt={`${name}的头像`} /> : <span>{name.slice(0, 1)}</span>}
    </span>
  )
}
