<script setup lang="ts">
import { h, ref, computed, type Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NLayoutHeader,
  NMenu,
  NIcon,
  NButton,
  NDropdown,
  NAvatar,
  NSpace,
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  DashboardOutlined,
  WechatOutlined,
  UserOutlined,
  BookOutlined,
  NodeIndexOutlined,
  ShareAltOutlined,
  LogoutOutlined,
} from '@vicons/antd'
import { clearToken } from '@/api/client'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: '仪表盘', key: 'dashboard', icon: renderIcon(DashboardOutlined) },
  { label: '对话', key: 'conversations', icon: renderIcon(WechatOutlined) },
  { label: '学习画像', key: 'profile', icon: renderIcon(UserOutlined) },
  { label: '资源库', key: 'resources', icon: renderIcon(BookOutlined) },
  { label: '学习路径', key: 'learning-path', icon: renderIcon(NodeIndexOutlined) },
  { label: '知识图谱', key: 'knowledge-graph', icon: renderIcon(ShareAltOutlined) },
]

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/conversations')) return 'conversations'
  if (path.startsWith('/profile')) return 'profile'
  if (path.startsWith('/resources')) return 'resources'
  if (path.startsWith('/learning-path')) return 'learning-path'
  if (path.startsWith('/knowledge-graph')) return 'knowledge-graph'
  return 'dashboard'
})

function handleMenuUpdate(key: string) {
  const routeMap: Record<string, string> = {
    dashboard: '/dashboard',
    conversations: '/conversations',
    profile: '/profile',
    resources: '/resources',
    'learning-path': '/learning-path',
    'knowledge-graph': '/knowledge-graph',
  }
  router.push(routeMap[key] || '/dashboard')
}

function handleLogout() {
  clearToken()
  router.push('/login')
}

const userOptions = [
  { label: '退出登录', key: 'logout', icon: renderIcon(LogoutOutlined) },
]

function handleUserAction(key: string) {
  if (key === 'logout') handleLogout()
}
</script>

<template>
  <NLayout position="absolute">
    <!-- Top header -->
    <NLayoutHeader bordered style="height: 48px; padding: 0 16px; display: flex; align-items: center; justify-content: space-between">
      <span style="font-weight: 600; font-size: 16px">JavaScript 个性化学习平台</span>
      <NDropdown :options="userOptions" @select="handleUserAction">
        <NButton text>
          <NSpace align="center">
            <NAvatar :size="28" round>
              <NIcon><UserOutlined /></NIcon>
            </NAvatar>
          </NSpace>
        </NButton>
      </NDropdown>
    </NLayoutHeader>

    <NLayout has-sider position="absolute" style="top: 48px">
      <NLayoutSider
        bordered
        collapse-mode="width"
        :collapsed-width="64"
        :width="200"
        :collapsed="collapsed"
        show-trigger
        @collapse="collapsed = true"
        @expand="collapsed = false"
      >
        <NMenu
          v-model:value="activeKey"
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :options="menuOptions"
          @update:value="handleMenuUpdate"
        />
      </NLayoutSider>

      <NLayoutContent>
        <slot />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>
