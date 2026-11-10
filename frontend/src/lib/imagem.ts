/**
 * Reduz a foto no próprio celular antes de enviar.
 *
 * Print ou foto de comprovante sai do iPhone com 3 a 8 MB; em rede de rua
 * isso demora e às vezes estoura o limite de upload. Para conferir um Pix,
 * 1600 px no lado maior sobra. O servidor reprocessa de qualquer jeito
 * (`core.imagens.processar`) — isto só alivia o caminho.
 *
 * Se o navegador não conseguir decodificar (formato exótico), devolve o
 * arquivo original e deixa o servidor decidir.
 */

const LADO_MAXIMO = 1600
const QUALIDADE = 0.85

export async function reduzirImagem(arquivo: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(arquivo)
    const escala = Math.min(1, LADO_MAXIMO / Math.max(bitmap.width, bitmap.height))
    const largura = Math.round(bitmap.width * escala)
    const altura = Math.round(bitmap.height * escala)

    const canvas = document.createElement('canvas')
    canvas.width = largura
    canvas.height = altura
    const contexto = canvas.getContext('2d')
    if (!contexto) return arquivo
    contexto.drawImage(bitmap, 0, 0, largura, altura)
    bitmap.close()

    const blob = await new Promise<Blob | null>((resolver) =>
      canvas.toBlob(resolver, 'image/jpeg', QUALIDADE),
    )
    return blob && blob.size < arquivo.size ? blob : arquivo
  } catch {
    return arquivo
  }
}
