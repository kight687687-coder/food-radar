export const BENEFICIAL_ADDITIVE_NAMES = [
  '维生素C', '维生素E', 'β-胡萝卜素', '茶多酚', '姜黄素', '植酸',
  'D-异抗坏血酸钠', '抗坏血酸钠', '牛磺酸', '卵磷脂',
  '赤藓糖醇', '木糖醇', '麦芽糖醇', '山梨糖醇', '甜菊糖苷', '罗汉果甜苷',
  '碳酸钙', '硫酸锌', '硫酸亚铁',
]

export const AVOID_GROUPS = [
  {
    key: 'allergy', name: '过敏类', tone: 'danger', items: [
      ['peanut', '花生过敏'], ['nuts', '坚果过敏'], ['milk_allergy', '牛奶过敏'],
      ['egg', '鸡蛋过敏'], ['wheat', '小麦/麸质过敏'], ['soy', '大豆过敏'],
      ['seafood', '海鲜过敏'], ['sesame', '芝麻过敏'],
    ],
  },
  {
    key: 'intolerance', name: '不耐受类', tone: 'warning', items: [
      ['lactose', '乳糖不耐受'], ['fructose', '果糖不耐受'], ['caffeine', '咖啡因敏感'],
      ['alcohol', '酒精不耐受'], ['msg', '味精敏感'],
    ],
  },
  {
    key: 'preference', name: '主动回避类', tone: 'success', items: [
      ['trans_fat', '反式脂肪'], ['artificial_color', '人工色素'], ['artificial_sweet', '人工甜味剂'],
      ['preservative', '防腐剂'], ['hfcs', '高果糖浆'], ['nitrite', '亚硝酸盐'], ['flavor', '香精香料'],
    ],
  },
]

export const AVOID_NAMES = Object.fromEntries(AVOID_GROUPS.flatMap(group => group.items))
export const USER_TYPES = ['普通人群', '减肥', '健身', '儿童', '老人', '孕妇', '糖尿病', '心血管']
export const GENDERS = ['男', '女', '保密']
export const RELATIONSHIPS = ['本人', '伴侣', '孩子', '父母', '其他家人']
