// Merender teks dengan format minimal **tebal** dan `kode` tanpa innerHTML,
// sehingga teks dari user, nama berkas, atau output LLM tidak bisa menyisipkan HTML.
const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`)/g

export default function RichText({ text }) {
  if (!text) return null
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={i}>{part.slice(1, -1)}</code>
    }
    return part
  })
}
