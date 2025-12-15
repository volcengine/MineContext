// i18next-parser.config.js
module.exports = {
  // 1. 上下文与键值分隔符
  contextSeparator: '_',
  // 如果你的 Key 包含 '.' (例如 "error.message") 且你希望它在 JSON 中嵌套，请保持默认 '.'
  // 如果你使用自然语言作为 Key (例如 "Hello World")，建议设为 false 以避免意外分割
  keySeparator: '.',
  namespaceSeparator: ':',

  // 2. 备份与恢复
  // 设为 false，因为如果不慎覆盖，Git 才是最好的备份工具。生成 _old.json 文件通常会弄脏目录
  createOldCatalogs: false,

  // 3. 默认值策略 (高阶用法)
  // 最佳实践：对于源语言 (en-US)，默认值就是 Key 本身（如果 Key 是自然语言）
  // 对于其他语言 (zh-CN)，留空以便翻译人员识别
  defaultValue: (locale, namespace, key, value) => {
    console.log('Found Key:', key, locale, namespace, value)
    if (locale === 'en-US') {
      // 如果代码中已经有默认值 (t('key', 'default'))，使用代码中的值
      return value || key
    }
    return '' // 中文等其他语言留空，表示待翻译
  },

  // 4. 代码格式化
  indentation: 2,
  keepRemoved: true, // 保持 true 以防止代码临时注释导致翻译丢失

  // 5. 词法分析器 (Lexers)
  // 明确配置 jsx/tsx 的解析选项，确保能够提取组件属性中的翻译
  lexers: {
    ts: ['JavascriptLexer'],
    tsx: [
      {
        lexer: 'JsxLexer',
        functions: ['t', 'Trans'], // 提取 t() 函数和 <Trans> 组件
        attr: 'i18nKey', // 提取组件属性中的 Key
        componentFunctions: ['Trans'] // 提取 <Trans> 组件
      }
    ],
    js: ['JavascriptLexer'],
    jsx: [
      {
        lexer: 'JsxLexer',
        functions: ['t', 'Trans'],
        attr: 'i18nKey',
        componentFunctions: ['Trans']
      }
    ],
    default: ['JavascriptLexer']
  },

  // 6. 语言与过滤
  locales: ['zh-CN', 'en-US'],
  // 这里的 defaultNamespace 主要是指未指定 ns 时的归宿
  defaultNamespace: 'translation',

  // 7. 输出配置
  output: 'src/locales/$LOCALE/$NAMESPACE.json',

  // 8. 输入源 (保持你原有的 Monorepo 结构)
  input: [
    'src/renderer/**/*.{js,jsx,ts,tsx}',
    'src/main/**/*.{js,ts}',
    'src/preload/**/*.{js,ts}',
    'packages/**/*.{js,ts}',
    '!src/**/*.d.ts',
    '!**/node_modules/**'
  ],

  // 9. 排序 (对 Git 协作至关重要)
  sort: true,

  // 10. 日志
  verbose: true,

  // [新增] 如果 key 已经存在于 json 中，是否更新其默认值？
  // 通常设为 false，避免代码中的临时修改覆盖了翻译人员已经校对好的文案
  resetDefaultValueLocale: false
}
