import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      common: {
        language: {
          zh: '中文',
          en: 'English'
        },
        save: 'Save',
        get_started: 'Get started',
        ok: 'Confirm',
        cancel: 'Cancel'
      },
      sidebar: {
        home: 'Home',
        monitor: 'Screen Monitor',
        settings: 'Settings',
        summary: 'Summary',
        tutorial: 'Start With Tutorial'
      },
      tutorial: {
        modal: {
          title: 'Proactive Feed',
          subtitle: 'Here are some insights you should know',
          ok: 'I got it'
        }
      },
      vault: {
        max_depth_reached: 'Maximum folder depth of 5 levels reached.'
      },
      home: {
        title: 'Create with Context, Clarity from Chaos',
        description:
          'Home delivers your daily summaries, todos, tips and insights from your collected Contexts',
        latest_activity: {
          title: 'Latest activity',
          empty: 'No activity in the last 7 days.'
        },
        recent_creation: {
          title: 'Recent creation',
          empty: 'No creation in the last 7 days.'
        },
        recent_chat: {
          title: 'Recent chat',
          empty: 'No chats in the latest 7 days.',
          untitled: 'Untitled Conversation'
        },
        view: 'View',
        check: 'Check',
        proactive: 'Proactive',
        feed: 'Feed',
        empty_insight_tip: 'Proactive insights will appear here to help you',
        tip: 'Tip',
        daily_summary: 'Daily Summary',
        weekly_summary: 'Weekly Summary',
        new_notification: 'New Notification',
        todo: {
          today: 'Today',
          update_tip: 'Update at 8 am everyday'
        }
      },
      toast: {
        insight_deleted: 'Insight deleted'
      },
      monitor: {
        header: {
          title: 'Screen Monitor',
          description:
            'Screen Monitor captures anything on your screen and transforms it into intelligent, connected Contexts. All data stays local with full privacy protection',
          settings_only_after_stop: 'Settings can only be adjusted after Stop Recording.',
          start_recording: 'Start Recording',
          stop_recording: 'Stop Recording',
          settings: 'Settings',
          select_monitoring_window_tip:
            'Please click the settings button and select your monitoring window or screen.'
        },
        modal: {
          display_screenshot_title: 'Display Screenshot',
          display_screenshot_alt: 'Display Screenshot'
        },
        empty: {
          today_tip: 'Start screen recording, summarize every {{minutes}} minutes',
          nodata: 'No data available',
          permission_enable_tip: 'Enable screen recording permission, summary every {{minutes}} minutes',
          enable_permission: 'Enable Permission'
        },
        settings_modal: {
          title: 'Settings',
          cancel: 'Cancel',
          save: 'Save',
          record_interval: 'Record Interval',
          choose_what_to_record: 'Choose what to record',
          enable_recording_hours: 'Enable recording hours',
          set_recording_hours: 'Set recording hours',
          apply_to_days: 'Apply to days',
          weekday: 'Only weekday',
          everyday: 'Everyday',
          screen_label: 'Screen',
          window_label: 'Window',
          only_opened_apps_tip: 'Only opened applications can be selected'
        },
        date: {
          today: 'Today'
        },
        toast: {
          select_at_least_one: 'Please select at least one screen or window',
          download_started: 'Download has started'
        },
        errors: {
          permission_required: 'Screen recording permission is required.',
          load_image_failed: 'Failed to load image',
          unable_get_image_data: 'Unable to get image data'
        }
      },
      settings: {
        title: 'Select a AI model to start',
        subtitle: "Configure AI model and API Key, then you can start MineContext’s intelligent context capability",
        vision_title: 'Vision language model',
        embedding_title: 'Embedding model',
        fields: {
          model_name: 'Model name',
          base_url: 'Base URL',
          api_key: 'API Key'
        },
        placeholders: {
          vision_model: 'A VLM model with visual understanding capabilities is required.',
          base_url: 'Enter your base URL',
          api_key: 'Enter your API Key',
          embedding_model: 'Enter your embedding model name'
        },
        errors: {
          required: 'Cannot be empty',
          select_model: 'Please select AI model',
          key_required: 'Please enter your API key',
          select_platform: 'Please select Model Platform',
          save_failed: 'Failed to save settings'
        },
        toast: {
          save_success: 'Your API key saved successfully'
        }
      }
    }
  },
  zh: {
    translation: {
      common: {
        language: {
          zh: '中文',
          en: '英文'
        },
        save: '保存',
        get_started: '开始使用',
        ok: '确认',
        cancel: '取消'
      },
      sidebar: {
        home: '首页',
        monitor: '屏幕监控',
        settings: '设置',
        summary: '总结',
        tutorial: '新手引导'
      },
      tutorial: {
        modal: {
          title: '主动信息流',
          subtitle: '一些你需要了解的洞见',
          ok: '知道了'
        }
      },
      vault: {
        max_depth_reached: '文件夹层级已达上限（最多5层）'
      },
      home: {
        title: '用上下文创造，从混乱中获得清晰',
        description: '首页展示每日总结、待办、技巧等洞见，源自你的上下文',
        latest_activity: {
          title: '最近活动',
          empty: '最近7天没有活动'
        },
        recent_creation: {
          title: '最近创建',
          empty: '最近7天没有新建'
        },
        recent_chat: {
          title: '最近会话',
          empty: '最近7天没有会话',
          untitled: '未命名对话'
        },
        view: '查看',
        check: '查看',
        proactive: '主动',
        feed: '信息流',
        empty_insight_tip: '主动洞见会显示在这里，帮助你',
        tip: '技巧',
        daily_summary: '每日总结',
        weekly_summary: '每周总结',
        new_notification: '新通知',
        todo: {
          today: '今天',
          update_tip: '每天早上8点更新'
        }
      },
      toast: {
        insight_deleted: '洞见已删除'
      },
      monitor: {
        header: {
          title: '屏幕监控',
          description: '屏幕监控会捕获你的屏幕内容并转化为智能的上下文，数据本地存储，隐私可控',
          settings_only_after_stop: '仅在停止录制后才能调整设置',
          start_recording: '开始录制',
          stop_recording: '停止录制',
          settings: '设置',
          select_monitoring_window_tip: '请先点击设置选择要监控的窗口或屏幕'
        },
        modal: {
          display_screenshot_title: '显示截图',
          display_screenshot_alt: '显示截图'
        },
        empty: {
          today_tip: '开始屏幕录制，每{{minutes}}分钟自动截图并总结',
          nodata: '暂无数据',
          permission_enable_tip: '请开启屏幕录制权限，每{{minutes}}分钟进行AI总结',
          enable_permission: '开启权限'
        },
        settings_modal: {
          title: '设置',
          cancel: '取消',
          save: '保存',
          record_interval: '录制间隔',
          choose_what_to_record: '选择要录制的内容',
          enable_recording_hours: '启用录制时段',
          set_recording_hours: '设置录制时段',
          apply_to_days: '应用到日期',
          weekday: '仅工作日',
          everyday: '每天',
          screen_label: '屏幕',
          window_label: '窗口',
          only_opened_apps_tip: '仅可选择已打开的应用'
        },
        date: {
          today: '今天'
        },
        toast: {
          select_at_least_one: '请至少选择一个屏幕或窗口',
          download_started: '开始下载'
        },
        errors: {
          permission_required: '需要开启屏幕录制权限',
          load_image_failed: '图片加载失败',
          unable_get_image_data: '无法获取图片数据'
        }
      },
      settings: {
        title: '选择模型开始使用',
        subtitle: '配置模型与 API Key，即可开启 MineContext 的智能上下文能力',
        vision_title: '视觉语言模型',
        embedding_title: '向量模型',
        fields: {
          model_name: '模型名称',
          base_url: '接口地址',
          api_key: '密钥'
        },
        placeholders: {
          vision_model: '请选择具有视觉理解能力的模型',
          base_url: '请输入接口地址',
          api_key: '请输入密钥',
          embedding_model: '请输入向量模型名称'
        },
        errors: {
          required: '不能为空',
          select_model: '请选择模型',
          key_required: '请输入密钥',
          select_platform: '请选择模型平台',
          save_failed: '保存设置失败'
        },
        toast: {
          save_success: 'API Key 保存成功'
        }
      }
    }
  }
}

const stored = typeof window !== 'undefined' ? window.localStorage.getItem('lang') : null
const lng = stored || 'zh'

i18n.use(initReactI18next).init({
  resources,
  lng,
  fallbackLng: 'zh',
  interpolation: { escapeValue: false }
})

export default i18n
