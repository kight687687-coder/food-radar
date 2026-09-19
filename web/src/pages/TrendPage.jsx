import { useNavigate } from 'react-router-dom'
import { Page } from '../components/Page'

export function TrendPage() {
  const navigate = useNavigate()
  return <Page className="trend-page"><section className="develop-card"><img className="develop-image" src="/images/feature-icons/card-report.png" alt="" /><h1>报告卡正在开发中</h1><p>我们正在打磨更适合分享和保存的家庭饮食报告，后续会支持生成阶段性食品安全总结。</p><div><button className="button primary full" type="button" onClick={() => navigate('/scan')}>去识别配料表</button><button className="develop-link" type="button" onClick={() => navigate('/')}>返回首页</button></div></section></Page>
}
