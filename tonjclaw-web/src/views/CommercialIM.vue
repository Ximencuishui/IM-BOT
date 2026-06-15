<template>
  <div class="commercial-im-page">
    <Navbar />

    <section class="hero">
      <div class="hero-content">
        <div class="logo">AI <span>IMBot</span></div>
        <h1>商用IM平台</h1>
        <p>基于OpenIM构建的企业级即时通讯解决方案，为您的业务提供安全、高效的实时沟通能力</p>
        <div class="hero-tags">
          <span class="hero-tag">🔒 私有化部署</span>
          <span class="hero-tag">🛡️ 端到端加密</span>
          <span class="hero-tag">⚡ 毫秒级响应</span>
          <span class="hero-tag">📱 多端支持</span>
          <span class="hero-tag">🔧 开放API</span>
        </div>
        <div class="hero-buttons">
          <el-button size="large" type="primary" @click="goToLogin" style="font-weight: 600; padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><ArrowUpBold /></el-icon> 立即体验
          </el-button>
          <el-button size="large" plain @click="scrollToFeatures" style="padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><Box /></el-icon> 了解功能
          </el-button>
        </div>
      </div>
    </section>

    <section id="features" class="features-section">
      <h2 class="section-title">核心功能</h2>
      <p class="section-subtitle">基于OpenIM深度定制，提供企业级即时通讯全功能支持</p>
      <div class="features-grid">
        <div class="feature-card" v-for="(feature, index) in features" :key="index">
          <div class="feature-icon">{{ feature.icon }}</div>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.description }}</p>
          <ul class="feature-list">
            <li v-for="(item, iIndex) in feature.items" :key="iIndex">
              <el-icon><Check /></el-icon> {{ item }}
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="tech-architecture">
      <h2 class="section-title">技术架构</h2>
      <p class="section-subtitle">基于OpenIM开源IM框架，打造高可用、可扩展的企业级IM平台</p>
      <div class="architecture-diagram">
        <div class="layer">
          <div class="layer-title">客户端层</div>
          <div class="layer-items">
            <div class="layer-item">Web端</div>
            <div class="layer-item">iOS端</div>
            <div class="layer-item">Android端</div>
            <div class="layer-item">桌面端</div>
          </div>
        </div>
        <div class="layer">
          <div class="layer-title">SDK层</div>
          <div class="layer-items">
            <div class="layer-item">OpenIM SDK</div>
            <div class="layer-item">消息加密</div>
            <div class="layer-item">状态同步</div>
            <div class="layer-item">离线推送</div>
          </div>
        </div>
        <div class="layer">
          <div class="layer-title">服务层</div>
          <div class="layer-items">
            <div class="layer-item">消息服务</div>
            <div class="layer-item">用户服务</div>
            <div class="layer-item">群组服务</div>
            <div class="layer-item">存储服务</div>
          </div>
        </div>
        <div class="layer">
          <div class="layer-title">基础设施层</div>
          <div class="layer-items">
            <div class="layer-item">Kubernetes</div>
            <div class="layer-item">Redis集群</div>
            <div class="layer-item">MySQL/PostgreSQL</div>
            <div class="layer-item">MinIO存储</div>
          </div>
        </div>
      </div>
    </section>

    <section class="scenarios-section">
      <h2 class="section-title">应用场景</h2>
      <p class="section-subtitle">适用于各种企业级即时通讯场景，满足不同行业的沟通需求</p>
      <div class="scenarios-grid">
        <div class="scenario-card" v-for="(scenario, index) in scenarios" :key="index">
          <div class="scenario-icon">{{ scenario.icon }}</div>
          <h3>{{ scenario.title }}</h3>
          <p>{{ scenario.description }}</p>
          <div class="scenario-features">
            <span class="scenario-feature" v-for="(feature, fIndex) in scenario.features" :key="fIndex">{{ feature }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="security-section">
      <h2 class="section-title">安全保障</h2>
      <p class="section-subtitle">企业级安全架构，全方位保护您的通信数据</p>
      <div class="security-grid">
        <div class="security-item" v-for="(item, index) in securityFeatures" :key="index">
          <div class="security-icon">{{ item.icon }}</div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </div>
      </div>
    </section>

    <section class="pricing-section">
      <h2 class="section-title">定价方案</h2>
      <p class="section-subtitle">灵活的定价策略，满足不同规模企业的需求</p>
      <div class="pricing-grid">
        <div class="pricing-card" v-for="(plan, index) in pricingPlans" :key="index">
          <div class="pricing-badge" v-if="plan.badge">{{ plan.badge }}</div>
          <h3>{{ plan.name }}</h3>
          <div class="pricing-price">
            <span class="price-symbol">¥</span>
            <span class="price-value">{{ plan.price }}</span>
            <span class="price-period">{{ plan.period }}</span>
          </div>
          <p class="pricing-desc">{{ plan.description }}</p>
          <ul class="pricing-features">
            <li v-for="(feature, fIndex) in plan.features" :key="fIndex">
              <el-icon><Check /></el-icon> {{ feature }}
            </li>
          </ul>
          <el-button :type="plan.highlight ? 'primary' : 'default'" @click="selectPlan(plan)">
            {{ plan.cta }}
          </el-button>
        </div>
      </div>
    </section>

    <section class="stats-section">
      <h2 class="stats-title">商用IM平台能力</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-number">10万+</div>
          <div class="stat-desc">并发在线用户</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">50ms</div>
          <div class="stat-desc">平均消息延迟</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">99.99%</div>
          <div class="stat-desc">服务可用性</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">256位</div>
          <div class="stat-desc">AES加密</div>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ArrowUpBold, Box, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()

const goToLogin = () => {
  router.push('/login')
}

const scrollToFeatures = () => {
  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
}

const selectPlan = async (plan) => {
  const token = localStorage.getItem('token')
  
  if (!token) {
    ElMessage.warning('请先登录后再选择方案')
    router.push('/login')
    return
  }

  if (plan.name === '企业版') {
    ElMessage.info('企业版需要定制，请联系销售团队')
    return
  }

  try {
    const response = await axios.post('/api/order/create', {
      plan_name: plan.name,
      price: plan.price,
      period: plan.period
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (response.data.success) {
      ElMessage.success(`已创建 ${plan.name} 订单，请前往订单页面支付`)
      router.push('/user/subscriptions')
    } else {
      ElMessage.error(response.data.error || '创建订单失败')
    }
  } catch (error) {
    ElMessage.error('创建订单过程中发生错误')
  }
}

const features = [
  {
    icon: '💬',
    title: '实时消息通讯',
    description: '支持单聊、群聊、广播等多种消息模式，毫秒级消息送达',
    items: [
      '单聊/群聊消息',
      '@提及和回复',
      '消息已读回执',
      '离线消息推送'
    ]
  },
  {
    icon: '👥',
    title: '智能群组管理',
    description: '灵活的群组权限控制，支持千人级大群组',
    items: [
      '多级管理员',
      '群成员审批',
      '消息置顶',
      '群组禁言'
    ]
  },
  {
    icon: '📋',
    title: '客户管理系统',
    description: '集成客户资料管理，支持客户标签和分组',
    items: [
      '客户资料管理',
      '客户标签体系',
      '客户分组',
      '客户跟进记录'
    ]
  },
  {
    icon: '📦',
    title: '订单追踪推送',
    description: '实时订单状态推送，让客户随时掌握订单进度',
    items: [
      '订单状态推送',
      '物流信息同步',
      '自动催单提醒',
      '订单统计报表'
    ]
  },
  {
    icon: '🔔',
    title: '智能通知中心',
    description: '统一的通知管理，支持多渠道消息推送',
    items: [
      '系统通知',
      '业务提醒',
      '邮件/短信推送',
      '自定义通知'
    ]
  },
  {
    icon: '⚙️',
    title: '开放API接口',
    description: '丰富的RESTful API，快速集成现有业务系统',
    items: [
      '用户管理API',
      '消息发送API',
      '群组管理API',
      'WebSocket接口'
    ]
  }
]

const scenarios = [
  {
    icon: '🏪',
    title: '电商客服',
    description: '为电商平台提供即时客服能力，提升客户购物体验',
    features: ['在线客服', '订单查询', '售后处理', '智能回复']
  },
  {
    icon: '📦',
    title: '供应链协作',
    description: '连接供应商、仓库、配送员，实现供应链全流程协同',
    features: ['订单推送', '库存预警', '物流跟踪', '对账结算']
  },
  {
    icon: '🏢',
    title: '企业内部沟通',
    description: '替代传统办公软件，提供高效的企业内部沟通',
    features: ['部门群组', '文件共享', '会议通知', '审批流程']
  },
  {
    icon: '🏥',
    title: '医疗健康',
    description: '医患沟通、健康咨询、用药提醒等医疗场景',
    features: ['医患沟通', '健康监测', '用药提醒', '报告推送']
  },
  {
    icon: '🎓',
    title: '在线教育',
    description: '师生互动、作业提交、在线答疑等教育场景',
    features: ['班级群组', '作业提交', '在线答疑', '课程通知']
  },
  {
    icon: '🏦',
    title: '金融服务',
    description: '理财咨询、账户通知、风险预警等金融场景',
    features: ['理财咨询', '账户通知', '风险预警', '交易提醒']
  }
]

const securityFeatures = [
  {
    icon: '🔐',
    title: '端到端加密',
    description: '采用AES-256加密算法，确保消息传输和存储的安全性'
  },
  {
    icon: '🏠',
    title: '私有化部署',
    description: '支持本地私有化部署，数据完全自主可控'
  },
  {
    icon: '🛡️',
    title: '访问控制',
    description: '基于角色的权限管理，细粒度控制用户访问权限'
  },
  {
    icon: '📊',
    title: '审计日志',
    description: '完整的操作审计记录，满足合规审计要求'
  },
  {
    icon: '🚫',
    title: '敏感词过滤',
    description: '智能敏感词检测，自动过滤违规内容'
  },
  {
    icon: '🔑',
    title: '多因素认证',
    description: '支持短信、邮件、令牌等多种认证方式'
  }
]

const pricingPlans = [
  {
    name: '基础版',
    price: '999',
    period: '/月',
    description: '适合小型企业和团队使用',
    features: [
      '最多1000用户',
      '单聊/群聊功能',
      '基础群组管理',
      '1年数据存储',
      '邮件技术支持'
    ],
    cta: '开始使用',
    highlight: false
  },
  {
    name: '专业版',
    price: '2999',
    period: '/月',
    description: '适合中型企业和成长型团队',
    badge: '推荐',
    features: [
      '最多10000用户',
      '全功能消息系统',
      '高级群组管理',
      '3年数据存储',
      '客户管理系统',
      '工单技术支持',
      'API接口调用'
    ],
    cta: '立即开通',
    highlight: true
  },
  {
    name: '企业版',
    price: '定制',
    period: '',
    description: '适合大型企业和集团客户',
    features: [
      '无限用户数',
      '私有化部署',
      '定制化开发',
      '永久数据存储',
      '专属客户成功经理',
      '7x24小时技术支持',
      '全量API接口',
      'SLA服务保障'
    ],
    cta: '联系销售',
    highlight: false
  }
]
</script>

<style scoped>
.commercial-im-page {
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

.hero-tags {
  display: flex;
  gap: 14px;
  justify-content: center;
  margin-bottom: 48px;
  flex-wrap: wrap;
}

.hero-tag {
  background: rgba(255, 255, 255, 0.1);
  padding: 10px 22px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  transition: all 0.25s;
}

.hero-tag:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(129, 140, 248, 0.4);
}

.hero-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.features-section {
  padding: 120px 20px;
  background: #fff;
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

.features-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 28px;
}

.feature-card {
  background: #fff;
  padding: 40px 32px;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  border: 1px solid #e2e8f0;
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
  transform: scaleX(0);
  transition: transform 0.35s ease;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 32px rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.3);
}

.feature-card:hover::before {
  transform: scaleX(1);
}

.feature-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-bottom: 24px;
  transition: all 0.3s;
}

.feature-card:hover .feature-icon {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%);
  transform: scale(1.05);
}

.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
  color: #0f172a;
  font-weight: 600;
}

.feature-card p {
  color: #64748b;
  line-height: 1.7;
  font-size: 15px;
  margin-bottom: 20px;
}

.feature-list {
  list-style: none;
  padding: 0;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #475569;
  font-size: 14px;
}

.tech-architecture {
  padding: 120px 20px;
  background: #f8fafc;
}

.architecture-diagram {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.layer {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #e2e8f0;
}

.layer-title {
  font-size: 16px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 16px;
  text-align: center;
}

.layer-items {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.layer-item {
  background: #f1f5f9;
  padding: 10px 20px;
  border-radius: 12px;
  font-size: 14px;
  color: #475569;
}

.scenarios-section {
  padding: 120px 20px;
  background: #fff;
}

.scenarios-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 28px;
}

.scenario-card {
  background: #fff;
  padding: 36px;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  transition: all 0.3s;
}

.scenario-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.08);
  border-color: #6366f1;
}

.scenario-icon {
  font-size: 44px;
  margin-bottom: 16px;
}

.scenario-card h3 {
  font-size: 18px;
  margin-bottom: 12px;
  color: #0f172a;
  font-weight: 600;
}

.scenario-card p {
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 20px;
}

.scenario-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scenario-feature {
  font-size: 12px;
  padding: 6px 12px;
  background: rgba(99, 102, 241, 0.08);
  border-radius: 12px;
  color: #6366f1;
}

.security-section {
  padding: 120px 20px;
  background: #0f172a;
  color: #fff;
}

.security-section .section-title {
  color: #fff;
}

.security-section .section-subtitle {
  color: #94a3b8;
}

.security-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.security-item {
  background: rgba(255, 255, 255, 0.05);
  padding: 32px;
  border-radius: 16px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.security-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
}

.security-icon {
  font-size: 40px;
  margin-bottom: 16px;
}

.security-item h3 {
  font-size: 18px;
  margin-bottom: 10px;
  font-weight: 600;
}

.security-item p {
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.6;
}

.pricing-section {
  padding: 120px 20px;
  background: #f8fafc;
}

.pricing-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 32px;
}

.pricing-card {
  background: #fff;
  padding: 40px;
  border-radius: 24px;
  border: 2px solid #e2e8f0;
  text-align: center;
  position: relative;
  transition: all 0.3s;
}

.pricing-card:hover {
  transform: translateY(-8px);
}

.pricing-card:nth-child(2) {
  border-color: #6366f1;
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.15);
}

.pricing-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  padding: 6px 20px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.pricing-card h3 {
  font-size: 22px;
  margin-bottom: 16px;
  color: #0f172a;
  font-weight: 600;
}

.pricing-price {
  margin-bottom: 16px;
}

.price-symbol {
  font-size: 24px;
  color: #6366f1;
  font-weight: 600;
}

.price-value {
  font-size: 48px;
  font-weight: 800;
  color: #0f172a;
}

.price-period {
  font-size: 16px;
  color: #64748b;
}

.pricing-desc {
  color: #64748b;
  font-size: 14px;
  margin-bottom: 24px;
}

.pricing-features {
  list-style: none;
  padding: 0;
  margin-bottom: 32px;
  text-align: left;
}

.pricing-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  color: #475569;
  font-size: 14px;
  border-bottom: 1px solid #f1f5f9;
}

.pricing-features li:last-child {
  border-bottom: none;
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

  .features-grid {
    grid-template-columns: 1fr;
  }

  .scenarios-grid {
    grid-template-columns: 1fr;
  }

  .security-grid {
    grid-template-columns: 1fr;
  }

  .pricing-grid {
    grid-template-columns: 1fr;
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