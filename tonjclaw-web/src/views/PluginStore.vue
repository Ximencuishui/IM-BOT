<template>
  <div class="plugin-store-page">
    <Navbar />

    <section class="hero">
      <div class="hero-content">
        <div class="logo">AI <span>IMBot</span></div>
        <h1>插件商店</h1>
        <p>探索丰富的插件生态，为您的业务定制专属解决方案</p>
        <div class="hero-buttons">
          <el-button size="large" type="primary" @click="scrollToPlugins" style="font-weight: 600; padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><Grid /></el-icon> 浏览插件
          </el-button>
          <el-button size="large" plain @click="goToIndustryCases" style="padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><Briefcase /></el-icon> 行业案例
          </el-button>
        </div>
      </div>
    </section>

    <section class="search-section">
      <div class="search-container">
        <el-input
          v-model="searchQuery"
          placeholder="搜索插件..."
          prefix-icon="Search"
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="selectedCategory" placeholder="选择分类" class="category-select" @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="行业插件" value="industry" />
          <el-option label="知识库" value="knowledge" />
          <el-option label="问答库" value="qa" />
          <el-option label="解析算法" value="algorithm" />
          <el-option label="工具插件" value="tool" />
        </el-select>
        <el-select v-model="selectedIndustry" placeholder="选择行业" class="industry-select" @change="handleFilter">
          <el-option label="全部" value="" />
          <el-option label="海鲜批发" value="海鲜批发" />
          <el-option label="餐饮配送" value="餐饮配送" />
          <el-option label="火锅食材" value="火锅食材" />
          <el-option label="茶饮咖啡" value="茶饮咖啡" />
          <el-option label="旅行社" value="旅行社" />
          <el-option label="工地管理" value="工地管理" />
          <el-option label="教育培训" value="教育培训" />
          <el-option label="房产中介" value="房产中介" />
          <el-option label="配件批发" value="配件批发" />
          <el-option label="车队调度" value="车队调度" />
          <el-option label="水电五金" value="水电五金" />
          <el-option label="日料寿司" value="日料寿司" />
          <el-option label="烘焙甜品" value="烘焙甜品" />
          <el-option label="电动车配件" value="电动车配件" />
          <el-option label="手机零配件" value="手机零配件" />
        </el-select>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
    </section>

    <section class="featured-plugins">
      <h2 class="section-title">精选插件</h2>
      <p class="section-subtitle">经过官方认证的高质量插件，为您的业务提供专业支持</p>
      <div class="featured-grid">
        <div class="featured-card" v-for="(plugin, index) in featuredPlugins" :key="index">
          <div class="featured-badge">精选</div>
          <div class="plugin-icon">{{ plugin.icon }}</div>
          <h3>{{ plugin.name }}</h3>
          <p>{{ plugin.description }}</p>
          <div class="plugin-tags">
            <span class="plugin-tag" v-for="(tag, tIndex) in plugin.tags" :key="tIndex">{{ tag }}</span>
          </div>
          <div class="plugin-meta">
            <span class="meta-item"><el-icon><Star /></el-icon> {{ plugin.rating }}</span>
            <span class="meta-item"><el-icon><Download /></el-icon> {{ plugin.downloads }}</span>
          </div>
          <el-button type="primary" @click="installPlugin(plugin)">安装</el-button>
        </div>
      </div>
    </section>

    <section id="plugins" class="plugins-section">
      <h2 class="section-title">所有插件</h2>
      <div class="plugins-tabs">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="行业插件" name="industry">
            <div class="plugins-grid">
              <div class="plugin-card" v-for="(plugin, index) in filteredIndustryPlugins" :key="index">
                <div class="plugin-icon-large">{{ plugin.icon }}</div>
                <div class="plugin-content">
                  <h3>{{ plugin.name }}</h3>
                  <p class="plugin-desc">{{ plugin.description }}</p>
                  <div class="plugin-info">
                    <span class="industry-badge">{{ plugin.industry }}</span>
                    <span class="version-badge">v{{ plugin.version }}</span>
                  </div>
                  <div class="plugin-tags">
                    <span class="plugin-tag" v-for="(tag, tIndex) in plugin.tags" :key="tIndex">{{ tag }}</span>
                  </div>
                  <div class="plugin-footer">
                    <div class="stats">
                      <span><el-icon><Star /></el-icon> {{ plugin.rating }}</span>
                      <span><el-icon><Download /></el-icon> {{ plugin.downloads }}</span>
                    </div>
                    <el-button type="primary" size="small" @click="installPlugin(plugin)">安装</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="知识库" name="knowledge">
            <div class="plugins-grid">
              <div class="plugin-card" v-for="(plugin, index) in filteredKnowledgePlugins" :key="index">
                <div class="plugin-icon-large">{{ plugin.icon }}</div>
                <div class="plugin-content">
                  <h3>{{ plugin.name }}</h3>
                  <p class="plugin-desc">{{ plugin.description }}</p>
                  <div class="plugin-info">
                    <span class="industry-badge">{{ plugin.industry }}</span>
                    <span class="version-badge">v{{ plugin.version }}</span>
                  </div>
                  <div class="plugin-tags">
                    <span class="plugin-tag" v-for="(tag, tIndex) in plugin.tags" :key="tIndex">{{ tag }}</span>
                  </div>
                  <div class="plugin-footer">
                    <div class="stats">
                      <span><el-icon><Star /></el-icon> {{ plugin.rating }}</span>
                      <span><el-icon><Download /></el-icon> {{ plugin.downloads }}</span>
                    </div>
                    <el-button type="primary" size="small" @click="installPlugin(plugin)">安装</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="问答库" name="qa">
            <div class="plugins-grid">
              <div class="plugin-card" v-for="(plugin, index) in filteredQaPlugins" :key="index">
                <div class="plugin-icon-large">{{ plugin.icon }}</div>
                <div class="plugin-content">
                  <h3>{{ plugin.name }}</h3>
                  <p class="plugin-desc">{{ plugin.description }}</p>
                  <div class="plugin-info">
                    <span class="industry-badge">{{ plugin.industry }}</span>
                    <span class="version-badge">v{{ plugin.version }}</span>
                  </div>
                  <div class="plugin-tags">
                    <span class="plugin-tag" v-for="(tag, tIndex) in plugin.tags" :key="tIndex">{{ tag }}</span>
                  </div>
                  <div class="plugin-footer">
                    <div class="stats">
                      <span><el-icon><Star /></el-icon> {{ plugin.rating }}</span>
                      <span><el-icon><Download /></el-icon> {{ plugin.downloads }}</span>
                    </div>
                    <el-button type="primary" size="small" @click="installPlugin(plugin)">安装</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="解析算法" name="algorithm">
            <div class="plugins-grid">
              <div class="plugin-card" v-for="(plugin, index) in filteredAlgorithmPlugins" :key="index">
                <div class="plugin-icon-large">{{ plugin.icon }}</div>
                <div class="plugin-content">
                  <h3>{{ plugin.name }}</h3>
                  <p class="plugin-desc">{{ plugin.description }}</p>
                  <div class="plugin-info">
                    <span class="industry-badge">{{ plugin.industry }}</span>
                    <span class="version-badge">v{{ plugin.version }}</span>
                  </div>
                  <div class="plugin-tags">
                    <span class="plugin-tag" v-for="(tag, tIndex) in plugin.tags" :key="tIndex">{{ tag }}</span>
                  </div>
                  <div class="plugin-footer">
                    <div class="stats">
                      <span><el-icon><Star /></el-icon> {{ plugin.rating }}</span>
                      <span><el-icon><Download /></el-icon> {{ plugin.downloads }}</span>
                    </div>
                    <el-button type="primary" size="small" @click="installPlugin(plugin)">安装</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </section>

    <section class="stats-section">
      <h2 class="stats-title">插件生态数据</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-number">50+</div>
          <div class="stat-desc">可用插件</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">7</div>
          <div class="stat-desc">行业分类</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">10k+</div>
          <div class="stat-desc">累计安装</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">4.9</div>
          <div class="stat-desc">平均评分</div>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Grid, Briefcase, Star, Download, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()

const searchQuery = ref('')
const selectedCategory = ref('')
const selectedIndustry = ref('')
const activeTab = ref('industry')
const loading = ref(false)

onMounted(() => {
  loadPlugins()
})

const loadPlugins = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/plugin/market', {
      params: {
        category: selectedCategory.value || undefined,
        industry: selectedIndustry.value || undefined,
        search: searchQuery.value || undefined
      }
    })
    if (response.data.success && response.data.plugins) {
      const plugins = response.data.plugins
      industryPlugins.value = plugins.filter(p => p.category === 'industry')
      knowledgePlugins.value = plugins.filter(p => p.category === 'knowledge')
      qaPlugins.value = plugins.filter(p => p.category === 'qa')
      algorithmPlugins.value = plugins.filter(p => p.category === 'algorithm')
    }
  } catch (error) {
    ElMessage.error('获取插件列表失败，使用本地数据')
  } finally {
    loading.value = false
  }
}

const goToIndustryCases = () => {
  router.push('/industry-cases')
}

const scrollToPlugins = () => {
  document.getElementById('plugins')?.scrollIntoView({ behavior: 'smooth' })
}

const handleSearch = async () => {
  if (selectedCategory.value) {
    activeTab.value = selectedCategory.value
  }
  await loadPlugins()
}

const handleFilter = async () => {
  if (selectedCategory.value && selectedCategory.value !== activeTab.value) {
    activeTab.value = selectedCategory.value
  }
  await loadPlugins()
}

const handleTabChange = (tab) => {
  activeTab.value = tab
  selectedCategory.value = tab
}

const installPlugin = async (plugin) => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录后再安装插件')
    router.push('/login')
    return
  }

  try {
    const response = await axios.post('/api/plugin/install', {
      plugin_code: plugin.plugin_code || plugin.name
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (response.data.success) {
      ElMessage.success(`${plugin.name} 安装成功`)
    } else {
      ElMessage.error(response.data.error || '安装失败')
    }
  } catch (error) {
    ElMessage.error('安装过程中发生错误')
  }
}

const featuredPlugins = ref([
  {
    icon: '🦐',
    name: '海鲜批发插件',
    description: '专为海鲜批发商设计，支持急单处理、供应商管理和批发价管理',
    tags: ['急单处理', '截单提醒', '供应商管理', '业务报表'],
    rating: 4.9,
    downloads: '3,256'
  },
  {
    icon: '🍜',
    name: '餐饮配送插件',
    description: '专为餐饮门店设计，支持特色食材的智能识别和批量订单处理',
    tags: ['特色食材', '批量圈选', '增量操作', '日报表'],
    rating: 4.9,
    downloads: '2,847'
  },
  {
    icon: '📚',
    name: '教育培训插件',
    description: '支持课程管理、学员跟踪、AI学习助手和学习进度分析',
    tags: ['AI学习助手', '学习进度', '智能批改', '个性化推荐'],
    rating: 4.9,
    downloads: '1,289'
  },
  {
    icon: '🏗️',
    name: '工地管理插件',
    description: '支持工人考勤、工期管理、工程量统计和安全检查',
    tags: ['工人打卡', '天气关联', '安全检查', '质量管控'],
    rating: 4.8,
    downloads: '1,345'
  },
  {
    icon: '🍲',
    name: '火锅食材插件',
    description: '支持荤素分类统计、锅底口味备注提取、蘸料偏好识别',
    tags: ['荤素分类', '锅底备注', '蘸料识别', 'TOP排行'],
    rating: 4.8,
    downloads: '1,923'
  },
  {
    icon: '🧋',
    name: '茶饮咖啡插件',
    description: '服务奶茶店、咖啡店连锁门店的原料补货和多店汇总',
    tags: ['连锁管理', '糖度识别', '配方同步', '多店汇总'],
    rating: 4.9,
    downloads: '1,567'
  }
])

const industryPlugins = ref([
  {
    icon: '🦐',
    name: '海鲜批发插件',
    description: '专为海鲜批发商设计，支持急单处理、供应商管理和批发价管理',
    industry: '海鲜批发',
    version: '2.2.0',
    tags: ['急单处理', '截单提醒', '供应商管理'],
    rating: 4.9,
    downloads: '3,256'
  },
  {
    icon: '🍜',
    name: '餐饮配送插件',
    description: '专为餐饮门店设计，支持特色食材的智能识别和批量订单处理',
    industry: '餐饮配送',
    version: '2.1.0',
    tags: ['特色食材', '批量圈选', '增量操作'],
    rating: 4.9,
    downloads: '2,847'
  },
  {
    icon: '🍲',
    name: '火锅食材插件',
    description: '支持荤素分类统计、锅底口味备注提取、蘸料偏好识别',
    industry: '火锅食材',
    version: '2.0.5',
    tags: ['荤素分类', '锅底备注', '蘸料识别'],
    rating: 4.8,
    downloads: '1,923'
  },
  {
    icon: '🧋',
    name: '茶饮咖啡插件',
    description: '服务奶茶店、咖啡店连锁门店的原料补货和多店汇总',
    industry: '茶饮咖啡',
    version: '1.8.0',
    tags: ['连锁管理', '糖度识别', '配方同步'],
    rating: 4.9,
    downloads: '1,567'
  },
  {
    icon: '✈️',
    name: '旅行社插件',
    description: '支持旅游线路智能解析、报名管理和群消息自动回复',
    industry: '旅行社',
    version: '2.0.0',
    tags: ['线路解析', '自动回复', '报名管理'],
    rating: 4.8,
    downloads: '1,432'
  },
  {
    icon: '🏗️',
    name: '工地管理插件',
    description: '支持工人考勤、工期管理、工程量统计和安全检查',
    industry: '工地管理',
    version: '2.1.0',
    tags: ['工人打卡', '天气关联', '安全检查'],
    rating: 4.8,
    downloads: '1,345'
  },
  {
    icon: '📚',
    name: '教育培训插件',
    description: '支持课程管理、学员跟踪、AI学习助手和学习进度分析',
    industry: '教育培训',
    version: '2.0.0',
    tags: ['AI学习助手', '学习进度', '智能批改'],
    rating: 4.9,
    downloads: '1,289'
  },
  {
    icon: '🏠',
    name: '房产中介插件',
    description: '支持房源管理、客户管理、智能推荐和交易流程跟踪',
    industry: '房产中介',
    version: '1.9.0',
    tags: ['智能推荐', '客户分析', '交易跟踪'],
    rating: 4.7,
    downloads: '1,123'
  },
  {
    icon: '🏍️',
    name: '摩托车配件插件',
    description: '支持配件型号俗称、品牌代码和维修店快速下单',
    industry: '配件批发',
    version: '1.6.0',
    tags: ['型号识别', '配件俗称', '维修店模式'],
    rating: 4.7,
    downloads: '1,234'
  },
  {
    icon: '🚛',
    name: '车队调度插件',
    description: '支持车辆管理、任务调度、路线规划和运输跟踪',
    industry: '车队调度',
    version: '2.0.0',
    tags: ['实时监控', '任务调度', '路线优化'],
    rating: 4.8,
    downloads: '987'
  },
  {
    icon: '🔧',
    name: '水电五金插件',
    description: '支持临时加单、改单、规格备注识别，智能将订单自动拆解',
    industry: '水电五金',
    version: '1.5.0',
    tags: ['改单识别', '规格提取', '线路汇总'],
    rating: 4.6,
    downloads: '892'
  },
  {
    icon: '🍱',
    name: '日料寿司插件',
    description: '专为日料店设计，支持海鲜类、寿司材料、调料类智能识别',
    industry: '日料寿司',
    version: '1.4.0',
    tags: ['海鲜识别', '寿司套餐', '进口食材'],
    rating: 4.8,
    downloads: '678'
  },
  {
    icon: '🍞',
    name: '烘焙甜品插件',
    description: '支持面粉、黄油、奶油、糖类等烘焙原料识别和品牌备注',
    industry: '烘焙甜品',
    version: '1.3.0',
    tags: ['品牌识别', '原料分类', '消耗分析'],
    rating: 4.7,
    downloads: '543'
  },
  {
    icon: '⚡',
    name: '电动车配件插件',
    description: '支持电池、控制器、轮毂、电机等配件识别和大件区分',
    industry: '电动车配件',
    version: '1.2.0',
    tags: ['大件区分', '配件识别', '运输提示'],
    rating: 4.5,
    downloads: '421'
  },
  {
    icon: '📱',
    name: '手机零配件插件',
    description: '支持型号快速识别、图片文字备注解析和批量配单',
    industry: '手机零配件',
    version: '1.1.0',
    tags: ['型号识别', '图片备注', '批量配单'],
    rating: 4.6,
    downloads: '356'
  }
])

const knowledgePlugins = ref([
  {
    icon: '📚',
    name: '餐饮知识库',
    description: '餐饮行业专业知识文档，包含食材处理、烹饪技巧、食品安全等内容',
    industry: '餐饮配送',
    version: '1.0.0',
    tags: ['食材处理', '烹饪技巧', '食品安全'],
    rating: 4.8,
    downloads: '1,234'
  },
  {
    icon: '📖',
    name: '火锅知识库',
    description: '火锅行业专业知识，包含锅底配方、食材搭配、蘸料调制等',
    industry: '火锅食材',
    version: '1.0.0',
    tags: ['锅底配方', '食材搭配', '蘸料调制'],
    rating: 4.7,
    downloads: '876'
  },
  {
    icon: '📕',
    name: '茶饮知识库',
    description: '茶饮咖啡行业知识，包含茶类原料、饮品配方、制作工艺等',
    industry: '茶饮咖啡',
    version: '1.0.0',
    tags: ['茶类原料', '饮品配方', '制作工艺'],
    rating: 4.9,
    downloads: '654'
  }
])

const qaPlugins = ref([
  {
    icon: '❓',
    name: '餐饮FAQ',
    description: '餐饮行业常见问题解答，包含订单处理、配送流程、客户服务等',
    industry: '餐饮配送',
    version: '1.0.0',
    tags: ['订单处理', '配送流程', '客户服务'],
    rating: 4.6,
    downloads: '543'
  },
  {
    icon: '💬',
    name: '火锅FAQ',
    description: '火锅行业常见问题解答，包含食材保存、锅底选择、蘸料搭配等',
    industry: '火锅食材',
    version: '1.0.0',
    tags: ['食材保存', '锅底选择', '蘸料搭配'],
    rating: 4.5,
    downloads: '321'
  }
])

const algorithmPlugins = ref([
  {
    icon: '🧠',
    name: 'AI智能解析器',
    description: '基于大语言模型的智能解析算法，支持自然语言订单识别',
    industry: '通用',
    version: '2.0.0',
    tags: ['AI解析', '自然语言', '智能识别'],
    rating: 4.9,
    downloads: '3,456'
  },
  {
    icon: '🔍',
    name: '正则表达式解析器',
    description: '灵活的正则表达式解析引擎，支持自定义解析规则',
    industry: '通用',
    version: '1.5.0',
    tags: ['正则表达式', '自定义规则', '灵活配置'],
    rating: 4.7,
    downloads: '1,234'
  },
  {
    icon: '✨',
    name: '关键词匹配器',
    description: '基于关键词的订单解析算法，支持同义词和模糊匹配',
    industry: '通用',
    version: '1.3.0',
    tags: ['关键词', '同义词', '模糊匹配'],
    rating: 4.6,
    downloads: '876'
  }
])

const filteredIndustryPlugins = computed(() => {
  return filterPlugins(industryPlugins.value)
})

const filteredKnowledgePlugins = computed(() => {
  return filterPlugins(knowledgePlugins.value)
})

const filteredQaPlugins = computed(() => {
  return filterPlugins(qaPlugins.value)
})

const filteredAlgorithmPlugins = computed(() => {
  return filterPlugins(algorithmPlugins.value)
})

const filterPlugins = (plugins) => {
  return plugins.filter(plugin => {
    const matchesSearch = !searchQuery.value || 
      plugin.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      plugin.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    
    const matchesIndustry = !selectedIndustry.value || 
      plugin.industry === selectedIndustry.value
    
    return matchesSearch && matchesIndustry
  })
}
</script>

<style scoped>
.plugin-store-page {
  min-height: 100vh;
  font-family: var(--font-family);
  line-height: 1.6;
  color: var(--text-primary);
  overflow-x: hidden;
}

.hero {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  color: #fff;
  padding: 160px 20px 140px;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.25) 0%, transparent 40%),
              radial-gradient(circle at 80% 20%, rgba(236, 72, 153, 0.15) 0%, transparent 40%),
              radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.08) 0%, transparent 60%);
}

.hero-content {
  position: relative;
  z-index: 1;
}

.hero .logo {
  font-size: 52px;
  font-weight: 900;
  margin-bottom: 16px;
}

.hero .logo span {
  background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero h1 {
  font-size: 48px;
  margin-bottom: 24px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: -1px;
}

.hero p {
  font-size: 20px;
  opacity: 0.85;
  margin-bottom: 36px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
  color: #e2e8f0;
}

.hero-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.search-section {
  padding: 60px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.search-container {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 250px;
}

.category-select,
.industry-select {
  width: 150px;
}

.featured-plugins {
  padding: 100px 20px;
  background: #f8fafc;
}

.section-title {
  text-align: center;
  font-size: 36px;
  margin-bottom: 16px;
  color: #0f172a;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.section-subtitle {
  text-align: center;
  font-size: 17px;
  color: #64748b;
  margin-bottom: 72px;
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.7;
}

.featured-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 32px;
}

.featured-card {
  background: #fff;
  padding: 40px 32px;
  border-radius: 24px;
  border: 1px solid #e2e8f0;
  text-align: center;
  position: relative;
  transition: all 0.3s;
}

.featured-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.12);
  border-color: #6366f1;
}

.featured-badge {
  position: absolute;
  top: 20px;
  right: 20px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.plugin-icon {
  font-size: 56px;
  margin-bottom: 20px;
}

.featured-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
  color: #0f172a;
  font-weight: 600;
}

.featured-card p {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 20px;
}

.plugin-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
}

.plugin-tag {
  font-size: 12px;
  padding: 5px 12px;
  background: #f1f5f9;
  border-radius: 16px;
  color: #64748b;
}

.plugin-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 24px;
  color: #64748b;
  font-size: 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.plugins-section {
  padding: 100px 20px;
  background: #fff;
}

.plugins-tabs {
  max-width: 1400px;
  margin: 0 auto;
}

.plugins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 28px;
  margin-top: 32px;
}

.plugin-card {
  background: #fff;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex;
  gap: 24px;
  padding: 28px;
  transition: all 0.3s;
}

.plugin-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.08);
  border-color: #6366f1;
}

.plugin-icon-large {
  font-size: 48px;
  flex-shrink: 0;
}

.plugin-content {
  flex: 1;
}

.plugin-content h3 {
  font-size: 18px;
  margin-bottom: 8px;
  color: #0f172a;
  font-weight: 600;
}

.plugin-desc {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.plugin-info {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.industry-badge {
  font-size: 12px;
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.1);
  border-radius: 12px;
  color: #6366f1;
}

.version-badge {
  font-size: 12px;
  padding: 4px 10px;
  background: #f1f5f9;
  border-radius: 12px;
  color: #64748b;
}

.plugin-content .plugin-tags {
  justify-content: flex-start;
  margin-bottom: 16px;
}

.plugin-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats {
  display: flex;
  gap: 16px;
  color: #64748b;
  font-size: 13px;
}

.stats span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stats-section {
  padding: 100px 20px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
}

.stats-title {
  text-align: center;
  font-size: 36px;
  margin-bottom: 60px;
  font-weight: 800;
}

.stats-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 40px;
}

.stat-item {
  text-align: center;
  padding: 30px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
}

.stat-number {
  font-size: 56px;
  font-weight: 900;
  margin-bottom: 10px;
}

.stat-desc {
  font-size: 16px;
  opacity: 0.9;
}

@media (max-width: 768px) {
  .hero h1 {
    font-size: 32px;
  }

  .hero p {
    font-size: 17px;
  }

  .hero-buttons {
    flex-direction: column;
    align-items: center;
  }

  .search-container {
    flex-direction: column;
  }

  .search-input,
  .category-select,
  .industry-select {
    width: 100%;
  }

  .featured-grid {
    grid-template-columns: 1fr;
  }

  .plugins-grid {
    grid-template-columns: 1fr;
  }

  .plugin-card {
    flex-direction: column;
    text-align: center;
  }

  .plugin-content .plugin-tags {
    justify-content: center;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .stat-number {
    font-size: 32px;
  }
}
</style>