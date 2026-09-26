import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import * as storage from '../services/storage'
import { clearImages } from '../services/imageStore'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [revision, setRevision] = useState(0)
  const [toast, setToast] = useState(null)
  const [dialog, setDialog] = useState(null)

  const initialProfile = storage.getProfile()
  storage.initializeFamily(initialProfile)
  const profile = storage.getProfile()
  const members = storage.getMembers()
  const activeMemberId = storage.getActiveMemberId()
  const activeMember = members.find(member => member.memberId === activeMemberId) || members[0] || null
  const history = storage.getHistory()
  const memberHistory = activeMember
    ? history.filter(record => !record.memberId || record.memberId === activeMember.memberId)
    : history

  const refresh = useCallback(() => setRevision(value => value + 1), [])

  const notify = useCallback((message, tone = 'neutral') => {
    setToast({ id: Date.now(), message, tone })
  }, [])

  const dismissToast = useCallback(() => setToast(null), [])

  const confirm = useCallback((options) => new Promise(resolve => {
    setDialog({
      title: options.title || '请确认',
      message: options.message,
      confirmLabel: options.confirmLabel || '确认',
      danger: Boolean(options.danger),
      resolve,
    })
  }), [])

  const settleDialog = useCallback((answer) => {
    setDialog(current => {
      current?.resolve(answer)
      return null
    })
  }, [])

  const saveUserProfile = useCallback((nextProfile) => {
    storage.saveProfile(nextProfile)
    storage.initializeFamily(nextProfile)
    refresh()
  }, [refresh])

  const selectMember = useCallback((memberId) => {
    storage.setActiveMemberId(memberId)
    refresh()
  }, [refresh])

  const createMember = useCallback((data) => {
    const result = storage.addMember(data)
    refresh()
    return result
  }, [refresh])

  const editMember = useCallback((memberId, data) => {
    const result = storage.updateMember(memberId, data)
    refresh()
    return result
  }, [refresh])

  const removeMember = useCallback((memberId) => {
    const result = storage.deleteMember(memberId)
    refresh()
    return result
  }, [refresh])

  const addRecord = useCallback((record) => {
    const result = storage.addHistoryRecord(record, storage.getActiveMemberId())
    refresh()
    return result
  }, [refresh])

  const renameRecord = useCallback((recordId, foodName) => {
    storage.updateHistoryRecord(recordId, { foodName })
    refresh()
  }, [refresh])

  const clearRecords = useCallback(async () => {
    storage.clearHistory()
    await clearImages().catch(() => {})
    refresh()
  }, [refresh])

  const value = useMemo(() => ({
    revision,
    profile,
    members,
    activeMember,
    activeMemberId,
    history,
    memberHistory,
    toast,
    dialog,
    refresh,
    notify,
    dismissToast,
    confirm,
    settleDialog,
    saveUserProfile,
    selectMember,
    createMember,
    editMember,
    removeMember,
    addRecord,
    renameRecord,
    clearRecords,
  }), [
    revision, profile, members, activeMember, activeMemberId, history, memberHistory,
    toast, dialog, refresh, notify, dismissToast, confirm, settleDialog, saveUserProfile, selectMember,
    createMember, editMember, removeMember, addRecord, renameRecord, clearRecords,
  ])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used inside AppProvider')
  return context
}
