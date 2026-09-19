import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { FeedbackLayer } from './FeedbackLayer'

const tabs = [
  { to: '/', label: '首页', icon: '/images/tabbar/home.png', activeIcon: '/images/tabbar/home-active.png' },
  { to: '/report', label: '档案', icon: '/images/tabbar/report.png', activeIcon: '/images/tabbar/report-active.png' },
  { to: '/scan', label: '扫一扫', icon: '/images/action-icons/scan-action-3d.png', activeIcon: '/images/action-icons/scan-action-3d.png', primary: true },
  { to: '/toolbox', label: '探索', icon: '/images/tabbar/explore.png', activeIcon: '/images/tabbar/explore-active.png' },
  { to: '/mine', label: '我的', icon: '/images/tabbar/mine.png', activeIcon: '/images/tabbar/mine-active.png' },
]

const detailLinks = [
  { to: '/wiki', label: '添加剂百科' },
  { to: '/compare', label: '配料表 PK' },
  { to: '/ai-chat', label: 'AI 营养师' },
  { to: '/history', label: '扫描历史' },
]

export function AppShell() {
  const location = useLocation()
  const hideNavigation = location.pathname === '/profile'
  const showMobileTabs = ['/', '/report', '/scan', '/toolbox', '/mine'].includes(location.pathname)

  return (
    <div className={`app-shell ${hideNavigation ? 'without-navigation' : ''} ${showMobileTabs ? '' : 'without-mobile-tabs'}`}>
      {!hideNavigation && (
        <aside className="desktop-rail" aria-label="主导航">
          <NavLink className="brand-mark" to="/" aria-label="食安雷达首页">
            <span className="brand-radar"><img src="/images/tabbar/scan-3d.png" alt="" /></span>
            <span><strong>食安雷达</strong><small>家庭食品安全管家</small></span>
          </NavLink>
          <nav className="rail-tabs">
            {tabs.map(item => <RailLink key={item.to} {...item} />)}
          </nav>
          <div className="rail-divider" />
          <nav className="rail-secondary" aria-label="快捷入口">
            {detailLinks.map(item => <NavLink key={item.to} to={item.to}>{item.label}</NavLink>)}
          </nav>
          <div className="rail-assistant">
            <img src="/images/ai-nutritionist-avatar.png" alt="" />
            <span>饮食疑问可直接问 AI 营养师</span>
          </div>
        </aside>
      )}

      <main className="app-main">
        <div className="route-stage" key={location.pathname}>
          <Outlet />
        </div>
      </main>

      {!hideNavigation && showMobileTabs && (
        <nav className="bottom-tabs" aria-label="主导航">
          {tabs.map(item => <RailLink key={item.to} {...item} />)}
        </nav>
      )}
      <FeedbackLayer />
    </div>
  )
}

function RailLink({ to, label, icon, activeIcon, primary }) {
  return (
    <NavLink to={to} end={to === '/'} className={({ isActive }) => `tab-link ${primary ? 'tab-primary' : ''} ${isActive ? 'active' : ''}`}>
      {({ isActive }) => (
        <>
          <span className="tab-icon"><img src={isActive ? activeIcon : icon} alt="" /></span>
          <span>{label}</span>
        </>
      )}
    </NavLink>
  )
}
