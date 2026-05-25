<script setup lang="ts">
/** Renders markdown content with highlight.js syntax highlighting.
 * Supports streaming mode with 50ms debounced re-render.
 */
import { watch } from 'vue'
import { useStreamingMarkdown } from '@/composables/useStreamingMarkdown'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const { renderedHtml, setContent, appendToken, reset } = useStreamingMarkdown()

let lastLength = 0

watch(
  () => props.content,
  (val) => {
    if (!props.isStreaming) {
      setContent(val)
    } else if (val.length > lastLength) {
      const delta = val.slice(lastLength)
      appendToken(delta)
      lastLength = val.length
    }
  },
  { immediate: true }
)

watch(
  () => props.isStreaming,
  (streaming) => {
    if (streaming) {
      reset()
      lastLength = 0
      setContent(props.content)
    }
  }
)
</script>

<template>
  <div class="markdown-body" v-html="renderedHtml" />
</template>

<style>
@import 'highlight.js/styles/github.css';

.markdown-body {
  line-height: 1.7;
  word-break: break-word;
}

.markdown-body pre {
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-body code {
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 0.9em;
}

.markdown-body pre code {
  background: #f6f8fa;
  display: block;
  padding: 16px;
}

.markdown-body p code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
