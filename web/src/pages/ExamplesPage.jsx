import { useNavigate } from 'react-router-dom'
import { OriginalIcon } from '../components/OriginalIcon'
import { Card, Page, Section } from '../components/Page'
import { EXAMPLE_FOODS } from '../data/exampleFoods'
import { setLastResult } from '../services/storage'

export function ExamplesPage() {
  const navigate = useNavigate()

  function startExample(item) {
    setLastResult({ ...item.result, imageSrc: item.imageSrc, exampleId: item.id })
    navigate('/result')
  }

  return (
    <Page title="示例食品" subtitle="选择一款，查看完整食品安全分析" back className="examples-page">
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
      <Section>
        <Card as="button" className="example-upload" type="button" onClick={() => navigate('/scan')}>
          <span><strong>上传自己的配料表</strong><small>使用真实图片开始分析</small></span>
          <OriginalIcon name="arrow-right" />
        </Card>
      </Section>
    </Page>
  )
}
