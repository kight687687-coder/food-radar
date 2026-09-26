import { useNavigate } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { EXAMPLE_FOODS, getExampleComparisonPreset } from '../data/exampleFoods'
import { setComparePreset, setLastResult } from '../services/storage'

export function ExamplesPage() {
  const navigate = useNavigate()

  function startExample(item) {
    setLastResult({ ...item.result, imageSrc: item.imageSrc, exampleId: item.id })
    navigate('/result')
  }

  function startExampleComparison() {
    const preset = getExampleComparisonPreset('xiaokaochang', 'ice-black-tea')
    if (preset) setComparePreset(preset)
    navigate('/compare')
  }

  return (
    <Page title="快速体验" subtitle="选择一种方式，快速了解食安雷达" back className="examples-page">
      <Section>
        <div className="example-grid">
          {EXAMPLE_FOODS.map(item => (
            <Card as="button" className="example-card" type="button" key={item.id} onClick={() => startExample(item)}>
              <img className="example-image" src={item.imageSrc} alt={`${item.name}配料表图片`} />
              <span className="example-card-copy">
                <strong>{item.name}</strong>
                <small>{item.category}</small>
                <span>{item.description}</span>
              </span>
              <span className="example-card-action">开始体验 <OriginalIcon name="arrow-right" /></span>
            </Card>
          ))}
        </div>
      </Section>
      <Section title="配料表 PK" subtitle="用两款常见食品，直接看评分与风险差异">
        <Card className="example-compare-card">
          <div className="example-compare-images">
            <img src="/images/demo/xiaokaochang.jpg" alt="小烤肠配料表图片" />
            <span>VS</span>
            <img src="/images/demo/ice-black-tea.jpg" alt="冰红茶配料表图片" />
          </div>
          <div className="example-compare-copy">
            <span><strong>小烤肠</strong><small>肉制品</small></span>
            <span><strong>冰红茶</strong><small>饮料</small></span>
          </div>
          <button className="button primary example-compare-action" type="button" onClick={startExampleComparison}>开始 PK <OriginalIcon name="arrow-right" /></button>
        </Card>
      </Section>
      <Section title="更多工具">
        <div className="example-tools-grid">
          <Card as="button" className="example-tool-card" type="button" onClick={() => navigate('/ai-chat')}>
            <span className="example-tool-icon"><OriginalIcon name="ai" /></span>
            <span><strong>AI 营养师</strong><small>咨询配料表、添加剂和饮食问题</small></span>
            <OriginalIcon name="arrow-right" />
          </Card>
          <Card as="button" className="example-tool-card" type="button" onClick={() => navigate('/wiki')}>
            <span className="example-tool-icon"><OriginalIcon name="book" /></span>
            <span><strong>150+ 种添加剂百科</strong><small>查询风险等级与人群提醒</small></span>
            <OriginalIcon name="arrow-right" />
          </Card>
        </div>
      </Section>
      <Section title="分析自己的食品">
        <button className="example-upload-action" type="button" onClick={() => navigate('/scan')}>
          <span className="example-upload-icon"><img src="/images/action-icons/camera-action-3d.png" alt="" /></span>
          <span><strong>拍照或上传配料表</strong><small>使用真实图片开始分析</small></span>
          <OriginalIcon name="arrow-right" />
        </button>
      </Section>
    </Page>
  )
}
