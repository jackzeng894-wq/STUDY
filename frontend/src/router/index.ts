import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '@/api/client'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { guest: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/pages/DashboardPage.vue'),
    },
    {
      path: '/conversations',
      name: 'Conversations',
      component: () => import('@/pages/ConversationListPage.vue'),
    },
    {
      path: '/conversations/:id',
      name: 'Conversation',
      component: () => import('@/pages/ConversationPage.vue'),
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/pages/ProfilePage.vue'),
    },
    {
      path: '/resources',
      name: 'Resources',
      component: () => import('@/pages/ResourceLibraryPage.vue'),
    },
    {
      path: '/resources/:id',
      name: 'ResourceDetail',
      component: () => import('@/pages/ResourceDetailPage.vue'),
    },
    {
      path: '/learning-path',
      name: 'LearningPaths',
      component: () => import('@/pages/LearningPathListPage.vue'),
    },
    {
      path: '/learning-path/:id',
      name: 'LearningPath',
      component: () => import('@/pages/LearningPathPage.vue'),
    },
    {
      path: '/knowledge-graph',
      name: 'KnowledgeGraph',
      component: () => import('@/pages/KnowledgeGraphPage.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/pages/SettingsPage.vue'),
    },
  ],
})

// Auth guard: redirect to login if not authenticated
router.beforeEach((to, _from, next) => {
  if (to.meta.guest) {
    // Login page — redirect to dashboard if already authenticated
    if (isAuthenticated()) {
      return next('/dashboard')
    }
    return next()
  }

  // All other routes require authentication
  if (!isAuthenticated()) {
    return next('/login')
  }

  return next()
})

export default router
