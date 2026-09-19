import { Component } from 'react'
import { KEYS } from '../services/storage'

export class AppErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Food Radar render failed', error, info)
  }

  reload = () => {
    window.location.reload()
  }

  resetAppData = () => {
    Object.values(KEYS).forEach(key => localStorage.removeItem(key))
    Object.keys(localStorage)
      .filter(key => key.startsWith('wiki_cache_') || key.startsWith('pkFullData_'))
      .forEach(key => localStorage.removeItem(key))
    window.location.assign('/profile')
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <main className="fatal-screen">
        <section className="fatal-card">
          <img src="/images/action-icons/scan-action-3d.png" alt="" />
          <h1>页面暂时没有正常显示</h1>
          <p>可以先刷新页面。如果旧版浏览器数据损坏，可清除本站本地数据后重新建立档案。</p>
          <div className="fatal-actions">
            <button className="button primary" type="button" onClick={this.reload}>刷新页面</button>
            <button className="button secondary" type="button" onClick={this.resetAppData}>清除本站数据</button>
          </div>
        </section>
      </main>
    )
  }
}
