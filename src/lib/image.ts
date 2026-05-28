export function resizeImageToDataUrl(file: File, maxSize = 720, quality = 0.72): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onerror = () => reject(new Error('画像の読み込みに失敗しました'))
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error('画像の変換に失敗しました'))
      image.onload = () => {
        const scale = Math.min(1, maxSize / Math.max(image.width, image.height))
        const canvas = document.createElement('canvas')
        canvas.width = Math.max(1, Math.round(image.width * scale))
        canvas.height = Math.max(1, Math.round(image.height * scale))

        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('画像処理を開始できませんでした'))
          return
        }

        ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/jpeg', quality))
      }
      image.src = String(reader.result)
    }

    reader.readAsDataURL(file)
  })
}
