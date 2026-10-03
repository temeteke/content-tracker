import vue from "@vitejs/plugin-vue"
import { defineConfig, loadEnv } from "vite"
import vuetify from "vite-plugin-vuetify"

const envDir = ".."

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, "VITE_")

  return {
    envDir,
    plugins: [vue(), vuetify({ autoImport: true })],
    server: {
      proxy: {
        "/api": env.VITE_DEV_PROXY_TARGET ?? "http://localhost:8000",
      },
    },
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.ts"],
    },
  }
})
