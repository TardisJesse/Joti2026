export async function prepareImage(file: File, maxSide = 1600): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Kies een JPG-, PNG- of WebP-foto.')
  if (file.size > 20 * 1024 * 1024) throw new Error('Kies een foto kleiner dan 20 MB.')
  const bitmap = await createImageBitmap(file)
  try {
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const context = canvas.getContext('2d')!
    context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const image = canvas.toDataURL('image/jpeg', 0.82)
    if (image.length > 2800000) throw new Error('Deze foto is te groot. Kies een kleinere foto.')
    return image
  } finally { bitmap.close() }
}
