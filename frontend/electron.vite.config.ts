// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import react from '@vitejs/plugin-react-swc'
import { CodeInspectorPlugin } from 'code-inspector-plugin'
import { resolve } from 'path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import { visualizer } from 'rollup-plugin-visualizer'
import tailwindcss from '@tailwindcss/vite'
// import react from '@vitejs/plugin-react'

const visualizerPlugin = (type: 'renderer' | 'main') => {
  return process.env[`VISUALIZER_${type.toUpperCase()}`] ? [visualizer({ open: true })] : []
}
const isDev = process.env.NODE_ENV === 'development'
// const isProd = process.env.NODE_ENV === 'production'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    resolve: {
      alias: {
        '@main': resolve('src/main'),
        '@types': resolve('src/renderer/src/types'),
        '@shared': resolve('packages/shared'),
        '@logger': resolve('src/main/services/LoggerService')
      }
    }
  },
  preload: {
    plugins: [
      react({
        tsDecorators: true
      }),
      externalizeDepsPlugin()
    ],
    resolve: {
      alias: {
        '@shared': resolve('packages/shared'),
        '@types': resolve('src/renderer/src/types')
      }
    },
    build: {
      sourcemap: isDev
    }
  },
  renderer: {
    resolve: {
      alias: {
        '@renderer': resolve('src/renderer/src'),
        '@shared': resolve('packages/shared'),
        '@logger': resolve('src/renderer/src/services/LoggerService'),
        '@types': resolve('src/renderer/src/types')
      }
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true
        }
      }
    },
    plugins: [
      tailwindcss(),
      react({
        // tsDecorators: true,
        // plugins: [
        //   [
        //     '@swc/plugin-styled-components',
        //     {
        //       displayName: true, // 开发环境下启用组件名称
        //       fileName: false, // 不在类名中包含文件名
        //       pure: true, // 优化性能
        //       ssr: false // 不需要服务端渲染
        //     }
        //   ]
        // ]
      }),
      ...(isDev ? [CodeInspectorPlugin({ bundler: 'vite' })] : []), // 只在开发环境下启用 CodeInspectorPlugin
      ...visualizerPlugin('renderer')
    ]
    // server: {
    //   proxy: {
    //     // 代理Express服务 (AI Chat)
    //     '/api/chat': {
    //       target: 'http://127.0.0.1:3001',
    //       changeOrigin: true,
    //       secure: false,
    //     },
    //   }
    // }
  }
})
