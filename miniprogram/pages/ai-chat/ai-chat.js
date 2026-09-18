const api = require('../../utils/request')
const family = require('../../utils/family')

const BOT_AVATAR = '/images/ai-nutritionist-avatar.png'

function cleanAnswer(text) {
  return String(text || '')
    .replace(/\*\*/g, '')
    .replace(/#{1,6}\s*/g, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

Page({
  data: {
    question: '',
    loading: false,
    botAvatar: BOT_AVATAR,
    userAvatar: '',
    userAvatarText: '我',
    messages: [
      {
        role: 'assistant',
        text: '你好，我是 AI 营养师。你可以问我配料表、食品添加剂、控糖减脂、儿童或孕妇饮食风险相关的问题。',
        avatar: BOT_AVATAR,
      }
    ],
    examples: [
      '山梨酸钾安全吗？',
      '儿童能喝含阿斯巴甜的饮料吗？',
      '配料表里哪些添加剂需要少吃？'
    ]
  },

  onLoad() {
    this.syncAvatar()
  },

  onShow() {
    this.syncAvatar()
  },

  syncAvatar() {
    const activeMember = family.getActiveMember && family.getActiveMember()
    const profile = wx.getStorageSync('userProfile') || {}
    const nickname = (activeMember && (activeMember.nickname || activeMember.relationship)) || profile.nickname || '我'
    this.setData({
      userAvatar: (activeMember && activeMember.avatar) || profile.avatar || '',
      userAvatarText: nickname.slice(0, 1) || '我',
    })
  },

  onInput(e) {
    this.setData({ question: e.detail.value })
  },

  useExample(e) {
    this.setData({ question: e.currentTarget.dataset.text })
  },

  sendQuestion() {
    const question = (this.data.question || '').trim()
    if (!question || this.data.loading) return

    const userMessage = {
      role: 'user',
      text: question,
      avatar: this.data.userAvatar,
      avatarText: this.data.userAvatarText,
    }
    // 仅保留最近8条消息作为上下文，控制接口请求体大小
    const history = this.data.messages.slice(-8).map(item => ({
      role: item.role,
      content: item.text,
    }))
    const messages = this.data.messages.concat([userMessage])
    this.setData({ messages, question: '', loading: true })

    api.aiChat(question, history)
      .then(res => {
        // 对AI回答做展示清洗，去除可能出现的Markdown格式
        const answer = cleanAnswer(res.answer || '暂时没有生成有效回答，请换个问法再试。')
        this.setData({
          messages: this.data.messages.concat([{ role: 'assistant', text: answer, avatar: BOT_AVATAR }]),
          loading: false,
        })
      })
      .catch(err => {
        // 接口失败时追加兜底回复，保持聊天流程连续
        this.setData({
          messages: this.data.messages.concat([
            { role: 'assistant', text: err.msg || 'AI 问答暂时不可用，请稍后再试。', avatar: BOT_AVATAR }
          ]),
          loading: false,
        })
      })
  }
})
