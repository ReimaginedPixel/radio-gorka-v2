import { createRouter, createWebHistory } from 'vue-router'
import Home from './page/Home.vue'
import AdminPanel from './page/AdminPanel.vue'
import NotFound from './page/404.vue'

const routes = [
  { path: '/', name: 'Home', component: Home, meta: { title: 'Radio Górka' } },
  { path: '/admin-panel', name: 'AdminPanel', component: AdminPanel, meta: { title: 'Panel DJ-a · Radio Górka' } },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound, meta: { title: 'Cisza w eterze · Radio Górka' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = to.meta.title || 'Radio Górka'
})

export default router
