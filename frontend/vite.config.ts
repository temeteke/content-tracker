import vue from "@vitejs/plugin-vue"
import { defineConfig, loadEnv } from "vite"

const envDir = ".."

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, "VITE_")

  return {
    envDir,
    plugins: [vue()],
    server: {
      proxy: {
        "/api": env.VITE_DEV_PROXY_TARGET ?? "http://localhost:8000",
      },
    },
  }
})
