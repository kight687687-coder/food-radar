import { useState } from 'react'
import { AVOID_GROUPS } from '../data/constants'
import { OriginalIcon } from './OriginalIcon'

export function AvoidSelector({ value = [], onChange }) {
  const [openGroups, setOpenGroups] = useState(() => new Set())

  function toggleGroup(key) {
    setOpenGroups(current => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function toggleItem(id) {
    onChange(value.includes(id) ? value.filter(item => item !== id) : [...value, id])
  }

  return (
    <div className="avoid-selector">
      {AVOID_GROUPS.map(group => {
        const open = openGroups.has(group.key)
        return (
          <div className="avoid-group" key={group.key}>
            <button type="button" className="avoid-group-toggle" onClick={() => toggleGroup(group.key)} aria-expanded={open}>
              <span>{group.name}</span>
              <OriginalIcon name="arrow-right" className={open ? 'open' : ''} />
            </button>
            {open && (
              <div className="avoid-options">
                {group.items.map(([id, name]) => {
                  const selected = value.includes(id)
                  return (
                    <button key={id} type="button" className={`avoid-option ${selected ? 'selected' : ''}`} onClick={() => toggleItem(id)} aria-pressed={selected}>
                      {name}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
