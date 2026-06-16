# 食安哨兵组件细节规则

本文档定义食安哨兵微信小程序的组件精修规则。它用于约束按钮、标签、图标、底部导航和空间密度，目标是让产品在统一的基础上保留清晰重点。

关联文档：

- `docs/design-system/information-architecture.md`

## 1. 目标

第三层组件精修的目标不是增加装饰，而是提升组件对齐、状态一致性、空间节奏和移动端触感。

关键词：

- 对齐
- 克制
- 稳定
- 微层次
- 可控例外

## 2. 状态色统一锚点

所有语义状态必须使用同一套色彩锚点。组件不能私自改 warning、danger、success 等语义色。

每个语义只允许有：

- base：核心色，用于强按钮、关键数字、重要图标。
- surface：浅底色，用于 tag、icon box、提示条背景。
- text：文字色，用于浅底上的文字。

### success

使用场景：

- 安全。
- 稳定。
- 正常。
- 已完成。

锚点：

```text
base: #07C160
surface: #E8F8EE
text: #049A4F
```

### warning

使用场景：

- 轻度关注。
- 近期风险。
- 需要留意。

锚点：

```text
base: #FF7D00
surface: #FFF3E6
text: #C45A00
```

### danger

使用场景：

- 高风险。
- 禁忌。
- 严重提醒。

锚点：

```text
base: #F53F3F
surface: #FFECEC
text: #C92A2A
```

### info

使用场景：

- 数据。
- 趋势。
- 工具。
- 普通信息。

锚点：

```text
base: #1677FF
surface: #EAF3FF
text: #1677FF
```

### ai

使用场景：

- AI。
- 画像。
- 个性化建议。

锚点：

```text
base: #7B61FF
surface: #F2EFFF
text: #7B61FF
```

### neutral

使用场景：

- 等待。
- 未生成。
- 普通说明。
- 低权重状态。

锚点：

```text
base: #86909C
surface: #F2F3F5
text: #4E5969
```

## 3. 组件强度等级

组件状态必须由“语义 + 强度”共同决定。

### weak

用于：

- 辅助标签。
- 列表状态。
- 普通提示。
- 图标浅底。

形式：

- surface 背景。
- text 文字。
- 无强阴影。

示例：

```text
warning-weak
info-weak
neutral-weak
```

### medium

用于：

- 当前状态。
- 重点标签。
- 页面内关键解释。

形式：

- surface 背景。
- text 文字。
- 更高字重或更明确边界。

示例：

```text
warning-medium
success-medium
danger-medium
```

### strong

用于：

- 首页主行动。
- 识别页上传主按钮。
- 高风险结果。
- 禁忌提醒。

形式：

- base 背景。
- 白色文字。
- 可有极轻层次，但不能营销化。

示例：

```text
success-strong
danger-strong
```

## 4. 密度档位

组件尺寸统一不等于页面节奏统一。页面必须选择密度档位，控制卡片内边距、模块间距、列表高度和图标空间。

### density-compact

适用场景：

- 历史记录列表。
- 设置列表。
- 二级页列表。

建议参数：

```text
card padding: 20-24rpx
section gap: 20-24rpx
list item min-height: 88-104rpx
icon box: sm
tag: sm
```

原则：

- 信息密度高。
- 但文字基线和分隔线必须清楚。

### density-default

适用场景：

- 普通一级页面模块。
- 档案页解释模块。
- 探索页工具模块。

建议参数：

```text
card padding: 28rpx
section gap: 28-32rpx
list item min-height: 104-120rpx
icon box: md
tag: md
```

原则：

- 默认使用。
- 保持稳定、不过分松散。

### density-relaxed

适用场景：

- 首页主卡。
- 识别页上传区。
- 结果页核心结论。

建议参数：

```text
card padding: 32-36rpx
section gap: 32-40rpx
main card min-height: 按内容定义
icon box: lg
tag: md
```

原则：

- 只用于 L1 或强任务场景。
- 不能全页面滥用。

## 5. 按钮规则

### 主按钮

适用：

- 首页立即扫描。
- 识别页上传。
- 结果页关键确认。

规则：

- 高度稳定，默认 88rpx。
- 字号 28-30rpx。
- 字重 800-900。
- 图标与文字间距 12-16rpx。
- 阴影极克制。
- 可有非常轻微的层次，但不能出现明显高光、强渐变、发光边缘。

禁止：

- 多个主按钮同时出现。
- 主按钮用于低频管理入口。
- 使用不同绿色或不同阴影私自变体。

### 次按钮

适用：

- 返回。
- 取消。
- 辅助操作。

规则：

- 使用白底、边框或 neutral surface。
- 不抢主按钮权重。
- 高度低于或等于主按钮。

### 文字按钮

适用：

- 查看全部。
- 管理。
- 编辑。
- 立即查询。

规则：

```text
font-size: 22rpx
font-weight: 800
color: success base
line-height: 1.3
```

要求：

- 与模块标题基线对齐。
- 不在页面内私自定义字号和字重。

## 6. 标签与徽章规则

### tag-sm

适用：

- 列表内状态。
- 小型补充说明。

建议参数：

```text
min-height: 36rpx
padding-x: 14rpx
font-size: 20rpx
font-weight: 800-900
border-radius: 999rpx
```

### tag-md

适用：

- 当前状态。
- 模块内重点标签。

建议参数：

```text
min-height: 40rpx
padding-x: 18rpx
font-size: 22rpx
font-weight: 800-900
border-radius: 999rpx
```

### 语义命名

推荐形式：

```text
fr-tag-success-weak
fr-tag-warning-weak
fr-tag-warning-medium
fr-tag-danger-medium
fr-tag-danger-strong
fr-tag-info-weak
fr-tag-ai-weak
fr-tag-neutral-weak
```

禁止：

- 同一种 warning 在不同页面使用不同橙色。
- 标签高度、内边距无规则变化。
- 大量 strong 标签同时出现。

## 7. 图标容器规则

图标精致度优先由容器尺寸、图标字号和语义色一致性决定。

### icon-box-sm

适用：

- 列表小图标。
- 辅助行图标。

建议参数：

```text
box: 44-48rpx
icon: 28-30rpx
radius: 16rpx
```

### icon-box-md

适用：

- 功能入口。
- 普通卡片图标。

建议参数：

```text
box: 64-76rpx
icon: 36-44rpx
radius: 16-20rpx
```

### icon-box-lg

适用：

- 主行动卡内图标。
- 上传区核心图标。

建议参数：

```text
box: 76-88rpx
icon: 44-52rpx
radius: 20rpx
```

规则：

- icon 颜色与容器背景必须使用同一语义锚点。
- 不同页面不能私自放大图标来制造重点。
- 同一功能组内图标视觉重量必须一致。

## 8. 底部导航规则

底部导航应像稳定工具栏，不像运营活动入口。

目标：

- 扫描入口明确突出。
- 整体悬浮感克制。
- 图标与文字对齐稳定。
- 选中态清楚但不过度。

规则：

- tabBar 阴影只用于轻分隔，不能重悬浮。
- 普通 Tab 选中态使用 success base + success surface。
- 未选中色固定使用 neutral base。
- 中间扫描按钮可以略大，但不能出现模糊光晕。
- 图标与文字垂直间距固定。
- 不通过过度放大制造选中态。

## 9. 执行顺序

第三层组件精修按以下顺序推进：

```text
1. app.wxss
   补充 tokens、状态色锚点、密度档位、基础组件。

2. 首页
   验证主卡、主按钮、标签、图标入口是否成立。

3. 扫描页
   验证高频强行动组件、上传区、任务态反馈是否成立。

4. tabBar
   在整体组件系统稳定后统一收口。

5. 其他页面批量替换
   档案、结果、探索、我的逐步收敛。
```

不建议先改 tabBar。tabBar 是全局气质收口，应在主页面组件规则稳定后精修。

## 10. 检查清单

每次改组件前检查：

- 当前组件属于 weak、medium 还是 strong？
- 当前状态使用的语义色是否来自统一锚点？
- 这个页面使用 compact、default 还是 relaxed 密度？
- 是否出现多个 strong 组件抢权重？
- 标签高度、padding、字号是否符合 sm/md 规则？
- 图标容器和图标字号是否匹配？
- 次要文字按钮是否与模块标题基线对齐？
- 底部导航是否过度发光或阴影过重？
- 是否为了“高级感”添加了不必要装饰？

## 11. 总结

组件精致度来自稳定规则，而不是更多样式。

最终判断标准：

```text
同一状态跨组件一致，
同一密度跨页面稳定，
强行动只在必要时突出，
其它元素安静地服务信息。
```
