<script setup lang="ts">
import { NInput, NButton } from 'naive-ui'

defineProps<{
  modelValue: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
}>()

function handleKeyup(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="message-input">
    <NInput
      type="textarea"
      :value="modelValue"
      :disabled="disabled"
      placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
      :autosize="{ minRows: 1, maxRows: 5 }"
      size="large"
      @update:value="(v: string) => emit('update:modelValue', v)"
      @keyup="handleKeyup"
    />
    <NButton
      type="primary"
      size="large"
      :disabled="disabled || !modelValue.trim()"
      @click="emit('send')"
    >
      发送
    </NButton>
  </div>
</template>

<style scoped>
.message-input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 16px;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.message-input :deep(.n-input) {
  flex: 1;
}
</style>
