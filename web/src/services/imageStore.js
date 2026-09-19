const DB_NAME = 'food-radar-media'
const STORE_NAME = 'images'

function openDatabase() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) {
      reject(new Error('当前浏览器不支持本地图片存储'))
      return
    }
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function transact(mode, action) {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, mode)
    const request = action(tx.objectStore(STORE_NAME))
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function saveImage(blob, key = `image_${Date.now()}_${Math.random().toString(36).slice(2)}`) {
  await transact('readwrite', store => store.put(blob, key))
  return key
}

export async function loadImage(key) {
  if (!key) return null
  return transact('readonly', store => store.get(key))
}

export async function deleteImage(key) {
  if (!key) return
  await transact('readwrite', store => store.delete(key))
}

export async function clearImages() {
  await transact('readwrite', store => store.clear())
}
