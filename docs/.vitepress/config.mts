import { createRequire } from 'module'
import { defineConfig, type DefaultTheme } from 'vitepress'

const require = createRequire(import.meta.url)
// const pypitoml = require('../../pyproject.toml')

const pkg = require('vitepress/package.json')

const version = "v0.0.1-pw.1"

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "F2",
  description: "Fast 2 Every",
  base: "/f2/",
  lastUpdated: true,

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/f2-logo.ico' }],
  ],
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
	  logo: { src: '/f2-logo.ico', width: 256, height: 256 },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/Johnserf-Seed/f2' },
      { icon: 'discord', link: 'https://discord.gg/3PhtPmgHf8' },
    ],
    algolia: {
      appId: '',
      apiKey: '',
      indexName: 'f2'
    },
    footer: {
      message: 'Released under the Apache-2.0 license.',
      copyright: 'Copyright © 2023-present Johnserf Seed'
    },
    editLink: {
      pattern: 'https://github.com/Johnserf-Seed/f2/edit/main/docs/:path',
      text: 'Edit this page on GitHub'
    }
  },

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh',
      themeConfig: {
        nav: cn_nav(),
        sidebar: {
          '/':[
            {
              text: '快速入门',
              items: [
                {text: '安装', link: '/install'},
                {text: '快速使用', link: '/quick-start'},
                {text: '进阶用法', link: '/advance-guide'},
              ]
            },
          ],
          '/guide/': [
            {
              text: '指南',
              items: [
                {text: '使用示例', link: '/api-examples'}
              ]
            }
          ],
        }
      }
    },

    en: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: en_nav(),
        sidebar: {
          '/':[
            {
              text: 'Quick Start',
              items: [
                {text: 'Install', link: '/en/install'},
                {text: 'Quick Start', link: '/en/quick-start'},
                {text: 'Advance Guide', link: '/en/advance-guide'},
              ]
            },
          ],
          '/guide/': [
            {
              text: 'Guide',
              items: [
                {text: 'API Examples', link: '/api-examples'}
              ]
            }
          ],
        }
      },
    }
  },
})

function cn_nav(): DefaultTheme.NavItem[] {
  return [
    {
      text: '指南',
      link: '/guide/what-is-f2',
      activeMatch: '/guide/'
    },
    {
      text: '参考',
      link: '/reference/site-config',
      activeMatch: '/reference/'
    },
    {
      //text: pkg.version,
      text: version,
      items: [
        {
          text: '更新日志',
          link: 'https://github.com/Johnserf-Seed/f2/blob/main/CHANGELOG.md'
        },
        {
          text: '贡献指南',
          link: 'https://github.com/Johnserf-Seed/f2/blob/main/.github/contributing.md'
        }
      ]
    }
  ]
}

function en_nav(): DefaultTheme.NavItem[] {
  return [
    {
      text: 'guide',
      link: '/en/guide/what-is-f2',
      activeMatch: '/guide/'
    },
    {
      text: 'reference',
      link: '/en/reference/site-config',
      activeMatch: '/reference/'
    },
    {
      //text: pkg.version,
      text: version,
      items: [
        {
          text: 'Changelog',
          link: 'https://github.com/Johnserf-Seed/f2/blob/main/CHANGELOG.md'
        },
        {
          text: 'Contributing',
          link: 'https://github.com/Johnserf-Seed/f2/blob/main/.github/contributing.md'
        }
      ]
    }
  ]
}
