import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    // 启用CSS代码分割
    cssCodeSplit: true,
    // 生成sourcemap - 生产环境关闭以提升构建速度
    sourcemap: false,
    // Rollup打包配置
    rollupOptions: {
      output: {
        // 手动分块，优化缓存 - rolldown 要求 manualChunks 为函数
        manualChunks(id) {
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia')) {
            return 'vendor-vue'
          }
          if (id.includes('node_modules/element-plus') || id.includes('node_modules/@element-plus')) {
            return 'vendor-element'
          }
          if (id.includes('node_modules/echarts')) {
            return 'vendor-echarts'
          }
          if (id.includes('node_modules/axios') || id.includes('node_modules/dayjs') || id.includes('node_modules/lodash-es')) {
            return 'vendor-utils'
          }
        }
      }
    },
    // 块大小警告限制(默认500KB)
    chunkSizeWarningLimit: 1000,
    // 启用treeshaking
    minify: 'esbuild',
    // 目标浏览器
    target: 'es2015'
  }
})