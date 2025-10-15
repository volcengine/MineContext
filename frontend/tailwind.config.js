// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/** @type {import('tailwindcss').Config} */

export default {
  // 添加前缀避免与 Arco Design 冲突（可选）
  // prefix: 'tw-',
  content: ['./src/renderer/index.html', './src/renderer/src/**/*.{js,ts,jsx,tsx}'],

  // 配置 CSS Reset 行为
  corePlugins: {
    // 保持 preflight，但我们通过 CSS 覆盖特定样式
    preflight: true
  },

  theme: {
    extend: {
      // 可以在这里添加自定义主题扩展
    }
  },
  plugins: [
    // 可以在这里添加插件
  ]
}
