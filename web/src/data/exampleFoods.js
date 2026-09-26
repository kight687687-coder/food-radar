const report = ({ summary, detail, suggestion, longTermRisk, judgment, recommendation }) => ({
  summary,
  detail,
  suggestion,
  long_term_risk: longTermRisk,
  judgment,
  recommendation,
})

export const EXAMPLE_FOODS = [
  {
    id: 'xiaokaochang',
    name: '小烤肠',
    category: '肉制品',
    imageSrc: '/images/demo/xiaokaochang.jpg',
    description: '查看肉制品配料与风险提示',
    result: {
      exampleId: 'xiaokaochang',
      food_category: '肉制品 · 小烤肠',
      ingredients: '鸡肉,猪肉,淀粉,大豆蛋白,白砂糖,食用盐,香辛料,山梨酸钾,亚硝酸钠',
      ingredients_count: 9,
      health_score: 62,
      risk_additives: [
        { name: '亚硝酸盐', risk_level: '中风险', deduct_score: 10, reason: '肉制品中常见的护色和防腐成分，需要关注食用频率。' },
        { name: '山梨酸钾', risk_level: '低风险', deduct_score: 5, reason: '用于防腐保鲜，建议结合配料表整体判断和食用频率。' },
      ],
      beneficial_ingredients: [
        { nutrient: '蛋白质', benefit_category: '蛋白质类' },
      ],
      group_warnings: [
        { warning: '肉制品钠含量通常需要结合营养成分表关注，建议控制单次份量。' },
      ],
      avoid_warnings: [],
      ai_report: report({
        summary: '小烤肠健康评分 62 分，建议适量食用。',
        detail: '这款肉制品包含肉类、淀粉和多种调味及加工成分，配料中需要重点留意亚硝酸盐和整体钠摄入。',
        suggestion: '建议偶尔食用并控制份量，搭配蔬菜和饮水；购买时可比较同类产品的配料长度和钠含量。',
        longTermRisk: '长期高频食用加工肉制品时，应留意整体盐摄入和饮食多样性。',
        judgment: '从当前配料看，产品能提供一定蛋白质，但加工和调味成分较多，适合作为偶尔食用的食品。',
        recommendation: '优先选择配料更短、钠含量更低的同类产品，避免把它作为日常主要蛋白来源。',
      }),
    },
  },
  {
    id: 'anmuxi-yogurt',
    name: '安慕希酸奶',
    category: '乳制品',
    imageSrc: '/images/demo/anmuxi-yogurt.jpg',
    description: '查看乳制品配料与营养信息',
    result: {
      exampleId: 'anmuxi-yogurt',
      food_category: '乳制品 · 安慕希酸奶',
      ingredients: '生牛乳,白砂糖,无水奶油,牛奶蛋白粉,淀粉,海藻酸钠,柠檬酸钠,德氏乳杆菌保加利亚亚种,嗜热链球菌',
      ingredients_count: 9,
      health_score: 84,
      risk_additives: [
        { name: '白砂糖', risk_level: '低风险', deduct_score: 5, reason: '含添加糖，建议结合每日总糖摄入和食用频率判断。' },
      ],
      beneficial_ingredients: [
        { nutrient: '蛋白质', benefit_category: '蛋白质类' },
        { nutrient: '乳酸菌', benefit_category: '益生菌类' },
        { nutrient: '钙', benefit_category: '矿物质类' },
      ],
      group_warnings: [],
      avoid_warnings: [],
      ai_report: report({
        summary: '安慕希酸奶健康评分 84 分，整体配料清晰。',
        detail: '配料表以生牛乳为主，含蛋白质、乳酸菌和钙等正向信息，同时含有白砂糖，适合结合个人饮食目标判断。',
        suggestion: '可以作为日常乳制品选择，注意查看每份糖含量，并根据个人情况控制摄入量。',
        longTermRisk: '长期饮用时可轮换无糖或低糖乳制品，保持乳制品来源多样。',
        judgment: '这款酸奶的主要原料是生牛乳，配料相对清晰；正向营养信息较多，但添加糖仍是需要留意的因素。',
        recommendation: '如果正在控糖，优先比较同类产品的碳水化合物和糖含量，或选择无糖酸奶。',
      }),
    },
  },
  {
    id: 'ice-black-tea',
    name: '冰红茶',
    category: '饮料',
    imageSrc: '/images/demo/ice-black-tea.jpg',
    description: '查看饮料配料与糖分提示',
    result: {
      exampleId: 'ice-black-tea',
      food_category: '饮料 · 冰红茶',
      ingredients: '水,果葡糖浆,白砂糖,浓缩红茶汁,浓缩柠檬汁,柠檬酸,柠檬酸钠,维生素C,食用盐,甜菊糖苷,焦糖色,食用香精',
      ingredients_count: 12,
      health_score: 57,
      risk_additives: [
        { name: '果葡糖浆', risk_level: '中风险', deduct_score: 10, reason: '饮料含有添加糖来源，建议关注饮用频率和总糖摄入。' },
        { name: '食用香精', risk_level: '低风险', deduct_score: 5, reason: '用于调节风味，建议结合整体配料和饮用频率判断。' },
        { name: '焦糖色', risk_level: '低风险', deduct_score: 5, reason: '用于调节色泽，建议结合整体配料和饮用频率判断。' },
      ],
      beneficial_ingredients: [
        { nutrient: '维生素C', benefit_category: '维生素类' },
      ],
      group_warnings: [
        { warning: '饮料中的糖分和甜味来源值得关注，儿童及控糖人群建议减少频率。' },
      ],
      avoid_warnings: [],
      ai_report: report({
        summary: '冰红茶健康评分 57 分，需要控制饮用频率。',
        detail: '配料中可见果葡糖浆、白砂糖和红茶汁，并含酸度调节剂与香精；维生素C属于正向信息，但不能抵消含糖饮料的整体提醒。',
        suggestion: '建议把白水或无糖茶作为日常饮品，冰红茶用于偶尔解馋，并留意每次饮用量。',
        longTermRisk: '长期高频饮用含糖饮料可能增加每日糖摄入，建议用饮水记录帮助控制频率。',
        judgment: '这款饮料的主要关注点是多种糖来源，维生素C只是配料中的补充信息，不代表可以忽略饮料的糖分。',
        recommendation: '选择无糖茶饮或白水作为替代；购买时优先比较营养成分表中的碳水化合物和糖含量。',
      }),
    },
  },
]

export function getExampleFood(id) {
  return EXAMPLE_FOODS.find(item => item.id === id) || null
}

export function isExampleResult(result) {
  return Boolean(result?.exampleId && getExampleFood(result.exampleId))
}
