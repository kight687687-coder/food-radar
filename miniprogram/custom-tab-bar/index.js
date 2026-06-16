const tabs = [
  {
    pagePath: 'pages/index/index',
    text: '首页',
    icon: 'icon-home',
    iconText: '\ue600',
    iconPath: '/images/tabbar/home.png',
    selectedIconPath: '/images/tabbar/home-active.png',
  },
  {
    pagePath: 'pages/report/report',
    text: '档案',
    icon: 'icon-folder',
    iconText: '\ue601',
    iconPath: '/images/tabbar/report.png',
    selectedIconPath: '/images/tabbar/report-active.png',
  },
  {
    pagePath: 'pages/scan/scan',
    text: '扫一扫',
    iconPath: '/images/tabbar/scan.png',
    selectedIconPath: '/images/tabbar/scan-active.png',
    actionIconPath: '/images/action-icons/scan-action-3d.png',
    featured: true,
  },
  {
    pagePath: 'pages/toolbox/toolbox',
    text: '探索',
    icon: 'icon-compass',
    iconText: '\ue603',
    iconPath: '/images/tabbar/explore.png',
    selectedIconPath: '/images/tabbar/explore-active.png',
  },
  {
    pagePath: 'pages/mine/mine',
    text: '我的',
    icon: 'icon-user',
    iconText: '\ue602',
    iconPath: '/images/tabbar/mine.png',
    selectedIconPath: '/images/tabbar/mine-active.png',
  },
]

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  data: {
    selected: 0,
    tabs,
  },

  lifetimes: {
    attached() {
      this.syncSelected()
    },
  },

  pageLifetimes: {
    show() {
      this.syncSelected()
    },
  },

  methods: {
    syncSelected() {
      const pages = getCurrentPages()
      const current = pages[pages.length - 1]
      const route = current ? current.route : ''
      const selected = tabs.findIndex(item => item.pagePath === route)
      if (selected >= 0 && selected !== this.data.selected) {
        this.setData({ selected })
      }
    },

    switchTab(e) {
      const index = Number(e.currentTarget.dataset.index)
      const item = this.data.tabs[index]
      if (!item || index === this.data.selected) return
      wx.switchTab({ url: '/' + item.pagePath })
    },
  },
})
