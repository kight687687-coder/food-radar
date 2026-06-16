var ALL_IDS = [
  'peanut', 'nuts', 'milk_allergy', 'egg', 'wheat', 'soy', 'seafood', 'sesame',
  'lactose', 'fructose', 'caffeine', 'alcohol', 'msg',
  'trans_fat', 'artificial_color', 'artificial_sweet', 'preservative', 'hfcs', 'nitrite', 'flavor',
]

Page({
  data: {
    sel_peanut: false,
    sel_nuts: false,
    sel_milk_allergy: false,
    sel_egg: false,
    sel_wheat: false,
    sel_soy: false,
    sel_seafood: false,
    sel_sesame: false,
    sel_lactose: false,
    sel_fructose: false,
    sel_caffeine: false,
    sel_alcohol: false,
    sel_msg: false,
    sel_trans_fat: false,
    sel_artificial_color: false,
    sel_artificial_sweet: false,
    sel_preservative: false,
    sel_hfcs: false,
    sel_nitrite: false,
    sel_flavor: false,
  },

  onLoad: function() {
    var profile = wx.getStorageSync('userProfile') || {}
    var saved = profile.selectedAvoids || []
    var obj = {}
    ALL_IDS.forEach(function(id) {
      obj['sel_' + id] = saved.indexOf(id) !== -1
    })
    this.setData(obj)
  },

  toggleItem: function(e) {
    var id = e.currentTarget.dataset.id
    var key = 'sel_' + id
    var obj = {}
    obj[key] = !this.data[key]
    this.setData(obj)
  },

  saveAndBack: function() {
    var data = this.data
    var ids = []
    ALL_IDS.forEach(function(id) {
      if (data['sel_' + id]) ids.push(id)
    })
    var profile = wx.getStorageSync('userProfile') || {}
    profile.selectedAvoids = ids
    wx.setStorageSync('userProfile', profile)
    wx.navigateBack()
  },
})
