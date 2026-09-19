export function ScoreRing({ score = 0, size = 136, label = '健康评分' }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0))
  const color = safeScore >= 80 ? '#07c160' : safeScore >= 60 ? '#ff7d00' : safeScore > 0 ? '#f53f3f' : '#c9cdd4'
  return (
    <div className="score-ring" style={{ '--score': `${safeScore * 3.6}deg`, '--ring-color': color, width: size, height: size }} aria-label={`${label} ${safeScore} 分`}>
      <div className="score-ring-inner">
        <strong>{safeScore}</strong>
        <span>{label}</span>
      </div>
    </div>
  )
}
