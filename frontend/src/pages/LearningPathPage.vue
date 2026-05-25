<script setup lang="ts">
/** Learning path detail: timeline + 3D knowledge graph + node cards. */
import { useRoute } from 'vue-router'
const route = useRoute()
const pathId = route.params.id as string
</script>
<template>
  <div style="padding: 24px">
    <h2>学习路径：{{ pathId }}</h2>
    <p>路径时间线 + 3D知识图谱 + 节点卡片 - 待实现</p>
  </div>
</template>
