import "@mdi/font/css/materialdesignicons.css"
import "vuetify/styles"

import { createPinia } from "pinia"
import { createApp } from "vue"
import { createVuetify } from "vuetify"
import App from "./App.vue"

createApp(App).use(createPinia()).use(createVuetify()).mount("#app")
