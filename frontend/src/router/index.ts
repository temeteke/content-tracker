import { createRouter, createWebHistory } from "vue-router"

import DetailView from "../views/DetailView.vue"
import ListView from "../views/ListView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "list", component: ListView },
    { path: "/items/:id", name: "detail", component: DetailView, props: true },
  ],
})

export default router
