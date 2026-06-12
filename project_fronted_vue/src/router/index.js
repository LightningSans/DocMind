import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '概览' },
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBaseList',
        component: () => import('@/views/KnowledgeBaseList.vue'),
        meta: { title: '知识库管理' },
      },
      {
        path: 'knowledge-bases/:id',
        name: 'KnowledgeBaseDetail',
        component: () => import('@/views/KnowledgeBaseDetail.vue'),
        meta: { title: '知识库详情' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '设置' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
