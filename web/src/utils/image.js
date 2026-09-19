export function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('无法读取图片'))
    reader.readAsDataURL(file)
  })
}

function loadHtmlImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片格式不受支持'))
    image.src = source
  })
}

export async function prepareImage(file, maxSize = 1800) {
  if (!file?.type?.startsWith('image/')) throw new Error('请选择图片文件')
  const source = await fileToDataUrl(file)
  const image = await loadHtmlImage(source)
  const scale = Math.min(1, maxSize / Math.max(image.naturalWidth, image.naturalHeight))
  const width = Math.max(1, Math.round(image.naturalWidth * scale))
  const height = Math.max(1, Math.round(image.naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  context.drawImage(image, 0, 0, width, height)
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.86))
  if (!blob) throw new Error('图片处理失败')
  const dataUrl = await fileToDataUrl(blob)
  return { blob, previewUrl: dataUrl, base64: dataUrl.split(',')[1], width, height }
}

export async function makeAvatarDataUrl(file) {
  const prepared = await prepareImage(file, 320)
  return prepared.previewUrl
}
