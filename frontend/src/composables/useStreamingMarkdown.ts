/** Streaming Markdown renderer with debounced re-render.

Accumulates raw tokens and re-renders markdown on a 50ms debounce
to avoid re-rendering on every single character during streaming.
*/

import { ref } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight: (str: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch {
        // fall through
      }
    }
    return '' // use external default escaping
  },
})

export function useStreamingMarkdown() {
  const rawContent = ref('')
  const renderedHtml = ref('')
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  function appendToken(token: string) {
    rawContent.value += token
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      renderedHtml.value = md.render(rawContent.value)
    }, 50)
  }

  function setContent(content: string) {
    rawContent.value = content
    renderedHtml.value = md.render(content)
  }

  function reset() {
    rawContent.value = ''
    renderedHtml.value = ''
    if (debounceTimer) clearTimeout(debounceTimer)
  }

  return { rawContent, renderedHtml, appendToken, setContent, reset }
}
