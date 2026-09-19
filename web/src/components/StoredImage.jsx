import { useEffect, useState } from 'react'
import { loadImage } from '../services/imageStore'
import { OriginalIcon } from './OriginalIcon'

export function StoredImage({ imageKey, src, alt = '', className = '' }) {
  const [url, setUrl] = useState(src || '')

  useEffect(() => {
    let active = true
    let objectUrl = ''
    if (src) return undefined
    if (!imageKey) return undefined
    loadImage(imageKey).then(blob => {
      if (active && blob) {
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      }
    }).catch(() => setUrl(''))
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [imageKey, src])

  const displayUrl = src || url
  if (!displayUrl) return <span className={`image-placeholder ${className}`} aria-hidden="true"><OriginalIcon name="list" /></span>
  return <img className={className} src={displayUrl} alt={alt} />
}
