import { describe, it, expect } from 'vitest'
import {
  formatStructuredText,
  formatDate,
  formatDateTime,
  formatCurrency,
  truncateText,
  formatFileSize,
  escapeText,
} from '../formatters.js'

// ===== formatStructuredText =====
describe('formatStructuredText', () => {
  it('空文本返回占位 span', () => {
    expect(formatStructuredText('')).toBe('<span class="fmt-empty">— 双击添加 —</span>')
    expect(formatStructuredText(null)).toBe('<span class="fmt-empty">— 双击添加 —</span>')
    expect(formatStructuredText(undefined)).toBe('<span class="fmt-empty">— 双击添加 —</span>')
    expect(formatStructuredText('   ')).toBe('<span class="fmt-empty">— 双击添加 —</span>')
  })

  it('支持自定义占位符', () => {
    expect(formatStructuredText('', '暂无内容')).toBe('<span class="fmt-empty">暂无内容</span>')
  })

  it('HTML 特殊字符被正确转义 (& < > " \')', () => {
    const result = formatStructuredText('a & b < c > d " e \' f')
    expect(result).toContain('&amp;')
    expect(result).toContain('&lt;')
    expect(result).toContain('&gt;')
    expect(result).toContain('&quot;')
    expect(result).toContain('&#39;')
    expect(result).not.toContain('&amp;lt;') // 不应双重转义
  })

  it('【title】格式创建 h5 标签', () => {
    expect(formatStructuredText('【标题】')).toBe('<h5 class="fmt-title">【标题】</h5>')
    // 标题后跟内容
    const withContent = formatStructuredText('【标题】内容文字')
    expect(withContent).toContain('<h5 class="fmt-title">【标题】</h5>')
    expect(withContent).toContain('<p class="fmt-text">内容文字</p>')
  })

  it('项目符号创建 ul/li 标签', () => {
    const result = formatStructuredText('• 第一项\n• 第二项')
    expect(result).toContain('<ul class="fmt-list">')
    expect(result).toContain('<li>第一项</li>')
    expect(result).toContain('<li>第二项</li>')
    expect(result).toContain('</ul>')
  })

  it('普通文本创建 p 标签', () => {
    expect(formatStructuredText('普通文本')).toBe('<p class="fmt-text">普通文本</p>')
  })

  it('XSS 攻击被转义，不执行脚本', () => {
    const xssInput = `<script>alert('xss')</script>`
    const result = formatStructuredText(xssInput)
    // 不应包含原始 <script> 标签
    expect(result).not.toContain('<script>')
    expect(result).not.toContain('</script>')
    // 应包含转义后的标签
    expect(result).toContain('&lt;script&gt;')
    expect(result).toContain('&lt;/script&gt;')
    // 应包含转义后的引号
    expect(result).toContain('&#39;xss&#39;')
  })
})


// ===== formatDate =====
describe('formatDate', () => {
  it('null/undefined 返回空字符串', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate(undefined)).toBe('')
    expect(formatDate('')).toBe('')
  })

  it('有效日期返回 YYYY-MM-DD 格式', () => {
    // 使用本地时间构造日期，避免时区问题
    const d = new Date(2026, 6, 23) // 2026-07-23 (月份从 0 开始)
    expect(formatDate(d)).toBe('2026-07-23')
  })

  it('ISO 字符串返回正确格式', () => {
    // 不带 Z 后缀的 ISO 字符串按本地时间解析
    expect(formatDate('2026-07-23T10:30:00')).toBe('2026-07-23')
  })
})


// ===== formatDateTime =====
describe('formatDateTime', () => {
  it('null/undefined 返回空字符串', () => {
    expect(formatDateTime(null)).toBe('')
    expect(formatDateTime(undefined)).toBe('')
    expect(formatDateTime('')).toBe('')
  })

  it('有效日期返回非空字符串', () => {
    const result = formatDateTime(new Date(2026, 6, 23, 10, 30, 0))
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})


// ===== formatCurrency =====
describe('formatCurrency', () => {
  it('null/undefined 返回空字符串', () => {
    expect(formatCurrency(null)).toBe('')
    expect(formatCurrency(undefined)).toBe('')
  })

  it('数字返回带千位分隔符的格式化字符串', () => {
    const result = formatCurrency(1234567)
    expect(result).toBeTruthy()
    // 应与原始数字字符串不同（说明添加了分隔符）
    expect(result).not.toBe('1234567')
  })
})


// ===== truncateText =====
describe('truncateText', () => {
  it('空文本返回空字符串', () => {
    expect(truncateText('')).toBe('')
    expect(truncateText(null)).toBe('')
    expect(truncateText(undefined)).toBe('')
  })

  it('短文本原样返回', () => {
    expect(truncateText('短文本')).toBe('短文本')
    expect(truncateText('hello world')).toBe('hello world')
  })

  it('长文本被截断并添加省略号', () => {
    const long = 'a'.repeat(100)
    const result = truncateText(long, 10)
    expect(result).toBe('a'.repeat(10) + '…')
    expect(result.length).toBe(11) // 10 个字符 + 1 个省略号
  })

  it('默认 maxLen 为 80', () => {
    const long = 'b'.repeat(100)
    const result = truncateText(long)
    expect(result).toBe('b'.repeat(80) + '…')
  })
})


// ===== formatFileSize =====
describe('formatFileSize', () => {
  it('0 返回 "0 B"', () => {
    expect(formatFileSize(0)).toBe('0 B')
  })

  it('1024 返回 "1 KB"', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
  })

  it('1048576 返回 "1 MB"', () => {
    expect(formatFileSize(1048576)).toBe('1 MB')
  })
})


// ===== escapeText =====
describe('escapeText', () => {
  it('null/undefined 返回空字符串', () => {
    expect(escapeText(null)).toBe('')
    expect(escapeText(undefined)).toBe('')
  })

  it('单引号被转义', () => {
    expect(escapeText("it's")).toBe("it\\'s")
  })

  it('双引号被转义', () => {
    expect(escapeText('say "hi"')).toBe('say \\"hi\\"')
  })

  it('反斜杠被转义', () => {
    expect(escapeText('a\\b')).toBe('a\\\\b')
  })

  it('无特殊字符的文本原样返回', () => {
    expect(escapeText('hello world')).toBe('hello world')
  })
})
