import vue from "@vitejs/plugin-vue"
import { defineConfig, loadEnv } from "vite"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")

  return {
    plugins: [vue()],
    server: {
      proxy: {
        "/api": env.VITE_DEV_PROXY_TARGET ?? "http://localhost:8000",
      },
    },
  }
})
