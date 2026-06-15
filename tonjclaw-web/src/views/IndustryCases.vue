<template>
  <div class="industry-cases-page">
    <Navbar />

    <section class="hero">
      <div class="hero-content">
        <div class="logo">AI <span>IMBot</span></div>
        <h1>行业案例</h1>
        <p>看AI IMBot如何帮助各行业企业提升效率、降低成本、实现数字化转型</p>
        <div class="hero-buttons">
          <el-button size="large" type="primary" @click="goToPluginStore" style="font-weight: 600; padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><ShoppingBag /></el-icon> 进入插件商店
          </el-button>
          <el-button size="large" plain @click="goToCommercialIM" style="padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><Message /></el-icon> 了解商用IM
          </el-button>
        </div>
      </div>
    </section>

    <section class="cases">
      <h2 class="section-title">真实应用场景</h2>
      <p class="section-subtitle">AI IMBot已经帮助500+企业实现IM订单自动化，平均效率提升90%+</p>
      <div class="case-grid">
        <div class="case-card" v-for="(caseItem, index) in cases" :key="index">
          <div class="case-header">
            <div class="case-header-content">
              <h3>{{ caseItem.icon }} {{ caseItem.title }}</h3>
              <span class="industry-tag">{{ caseItem.industry }}</span>
            </div>
          </div>
          <div class="case-body">
            <div class="case-problem">
              <h4><el-icon><CircleCloseFilled /></el-icon> 使用前痛点</h4>
              <p>{{ caseItem.problem }}</p>
            </div>
            <div class="case-solution">
              <h4><el-icon><CircleCheckFilled /></el-icon> AI IMBot解决方案</h4>
              <p>{{ caseItem.solution }}</p>
            </div>
            <div class="case-results">
              <h4><el-icon><TrendCharts /></el-icon> 使用效果</h4>
              <div class="result-item" v-for="(result, rIndex) in caseItem.results" :key="rIndex">
                <span class="result-label">{{ result.label }}</span>
                <span class="result-value">{{ result.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="stats-section">
      <h2 class="stats-title">AI IMBot 累计为客户创造的价值</h2>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-number">500+</div>
          <div class="stat-desc">服务企业客户</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">90%+</div>
          <div class="stat-desc">平均效率提升</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">80%</div>
          <div class="stat-desc">平均成本降低</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">99.5%</div>
          <div class="stat-desc">订单准确率</div>
        </div>
      </div>
    </section>

    <section class="industries-preview">
      <h2 class="section-title">覆盖行业</h2>
      <p class="section-subtitle">从餐饮配送、配件批发到水电五金，AI IMBot都能为您提供智能化的订单处理方案</p>
      <div class="industries-grid">
        <div class="industry-card" v-for="(industry, index) in industries" :key="index">
          <div class="industry-icon">{{ industry.icon }}</div>
          <div class="industry-content">
            <h3>{{ industry.name }}</h3>
            <p>{{ industry.description }}</p>
            <div class="industry-tags">
              <span class="industry-tag" v-for="(tag, tIndex) in industry.tags" :key="tIndex">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <Footer />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ShoppingBag, Message, CircleCloseFilled, CircleCheckFilled, TrendCharts } from '@element-plus/icons-vue'
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()

const goToPluginStore = () => {
  router.push('/plugin-store')
}

const goToCommercialIM = () => {
  router.push('/commercial-im')
}

const cases = [
  {
    icon: '🍜',
    title: '福州餐饮配送中心',
    industry: '餐饮配送',
    problem: '每天需要处理120+群组的订单消息，3名员工专职手动录入Excel，错误率高达15%，经常漏单错单，客户投诉频繁。',
    solution: '部署AI IMBot自动捕获IM订单，使用餐饮行业模板，自动识别特色食材，一键生成采购单和配送单。',
    results: [
      { label: '订单处理效率', value: '提升 92%' },
      { label: '人工成本节省', value: '减少 2人/天' },
      { label: '订单准确率', value: '提升至 99.5%' }
    ]
  },
  {
    icon: '🦐',
    title: '青岛海鲜批发商行',
    industry: '海鲜批发',
    problem: '每日处理500+客户订单，急单需要优先处理，人工难以区分订单优先级，供应商报价管理混乱，月底对账耗时。',
    solution: '使用海鲜批发行业模板，自动识别急单并通知老板，支持供应商报价管理和截单时间提醒，自动生成业务报表。',
    results: [
      { label: '急单处理时效', value: '缩短 85%' },
      { label: '供应商管理效率', value: '提升 70%' },
      { label: '对账时间', value: '从2天缩短至30分钟' }
    ]
  },
  {
    icon: '🍲',
    title: '成都火锅食材供应链',
    industry: '火锅食材',
    problem: '服务200+火锅店，每天订单量300+，需要区分荤素、锅底要求、蘸料偏好，手动分类耗时耗力，月底对账困难。',
    solution: '使用火锅店行业模板，自动识别荤素分类、锅底口味、蘸料偏好，自动生成日/周/月报表，支持多维度统计。',
    results: [
      { label: '分类统计时间', value: '从3小时缩短至5分钟' },
      { label: '客户满意度', value: '提升 45%' },
      { label: '月度对账效率', value: '提升 85%' }
    ]
  },
  {
    icon: '🧋',
    title: '连锁茶饮品牌区域配送',
    industry: '茶饮咖啡',
    problem: '管理50家门店原料补货，各店糖度要求、配料偏好不同，经常发错货，门店投诉多，库存管理混乱。',
    solution: '使用茶饮咖啡行业模板，自动识别糖度要求、配料偏好，支持按门店编号快捷下单，自动汇总各分店需求。',
    results: [
      { label: '发货准确率', value: '提升至 99.8%' },
      { label: '门店投诉率', value: '下降 78%' },
      { label: '库存周转率', value: '提升 35%' }
    ]
  },
  {
    icon: '✈️',
    title: '云南旅行社线路推广',
    industry: '旅行社',
    problem: '每天发布20+旅游线路，手动解析线路信息并转发到多个客户群，报名信息收集分散，客户反馈难以统计。',
    solution: '使用旅行社行业模板，自动解析旅游线路信息，智能回复客户咨询，自动收集报名信息并生成日报统计。',
    results: [
      { label: '线路发布效率', value: '提升 80%' },
      { label: '报名信息收集', value: '100% 自动化' },
      { label: '客户反馈响应', value: '平均 3分钟' }
    ]
  },
  {
    icon: '🏗️',
    title: '中建八局工地管理',
    industry: '工地管理',
    problem: '管理1000+工人考勤，手动记录工作量效率低下，天气影响工期难以跟踪，安全质量检查记录分散。',
    solution: '使用工地管理行业模板，支持工人定位打卡，天气与工期关联分析，安全隐患跟踪和质量管控，自动生成日报。',
    results: [
      { label: '考勤管理效率', value: '提升 95%' },
      { label: '工期延误率', value: '下降 60%' },
      { label: '安全隐患闭环', value: '100% 跟踪' }
    ]
  },
  {
    icon: '📚',
    title: '新东方教育培训',
    industry: '教育培训',
    problem: '管理5000+学员学习进度，作业批改耗时，个性化学习建议难以提供，课程推荐缺乏数据支撑。',
    solution: '使用教育培训行业模板，AI学习助手智能答疑，学习进度可视化跟踪，智能作业批改和个性化学习路径推荐。',
    results: [
      { label: '作业批改效率', value: '提升 90%' },
      { label: '学员留存率', value: '提升 40%' },
      { label: '个性化推荐准确率', value: '92%' }
    ]
  },
  {
    icon: '🏠',
    title: '链家房产中介',
    industry: '房产中介',
    problem: '管理10000+房源信息，客户需求匹配效率低，带看记录分散，交易流程难以跟踪。',
    solution: '使用房产中介行业模板，房源智能推荐，客户需求分析，带看记录管理和交易流程跟踪，市场数据分析。',
    results: [
      { label: '房源匹配效率', value: '提升 85%' },
      { label: '客户转化率', value: '提升 35%' },
      { label: '交易周期', value: '缩短 40%' }
    ]
  },
  {
    icon: '🍱',
    title: '日料食材进口配送商',
    industry: '日料寿司',
    problem: '进口海鲜食材价格高、保质期短，需要精准统计各店订单，避免浪费。手动统计容易出错，库存损耗率高。',
    solution: '使用日料寿司行业模板，精准识别海鲜食材，支持寿司套餐识别，自动生成采购计划，减少库存积压。',
    results: [
      { label: '库存损耗率', value: '降低 62%' },
      { label: '订单处理速度', value: '提升 88%' },
      { label: '年度节省成本', value: '¥280,000+' }
    ]
  },
  {
    icon: '🍞',
    title: '烘焙原料批发配送',
    industry: '烘焙甜品',
    problem: '服务100+烘焙店，原料种类繁多，品牌要求各异，手动记录品牌信息耗时且易错。',
    solution: '使用烘焙甜品行业模板，自动识别原料分类和品牌要求，支持效期管理提醒，自动生成周/月消耗分析报表。',
    results: [
      { label: '品牌错发率', value: '降至 0.5%以下' },
      { label: '采购计划准确率', value: '提升至 95%' },
      { label: '客户续约率', value: '提升至 98%' }
    ]
  },
  {
    icon: '🏍️',
    title: '摩托车配件批发中心',
    industry: '配件批发',
    problem: '配件型号复杂，客户口语化下单，经常配错型号，退货率高，客户流失严重。',
    solution: '使用配件批发行业模板，AI自动识别配件型号俗称、品牌代码，减少漏配和配错风险。',
    results: [
      { label: '型号识别准确率', value: '提升至 99%' },
      { label: '退货率', value: '下降 65%' },
      { label: '客户满意度', value: '提升 50%' }
    ]
  },
  {
    icon: '🚛',
    title: '顺丰车队调度中心',
    industry: '车队调度',
    problem: '管理200+车辆调度，手动分配任务效率低，车辆状态难以监控，维护保养记录分散，路线规划缺乏优化。',
    solution: '使用车队调度行业模板，支持手动/自动任务调度，实时车辆状态监控，维护保养提醒，路线规划优化和驾驶行为分析。',
    results: [
      { label: '调度效率', value: '提升 75%' },
      { label: '车辆利用率', value: '提升 30%' },
      { label: '油耗成本', value: '降低 20%' }
    ]
  }
]

const industries = [
  {
    icon: '🦐',
    name: '海鲜批发',
    description: '专为海鲜批发商设计，支持急单处理、供应商管理和批发价管理',
    tags: ['急单处理', '截单提醒', '供应商管理', '业务报表']
  },
  {
    icon: '🍜',
    name: '餐饮配送',
    description: '专为餐饮门店设计，支持特色食材的智能识别',
    tags: ['特色食材识别', '批量圈选', '增量操作', '日/周/月报表']
  },
  {
    icon: '🍲',
    name: '火锅食材配送',
    description: '支持荤素分类统计、锅底口味备注提取、蘸料偏好识别',
    tags: ['荤素分类', '锅底备注', '蘸料识别', 'TOP食材排行']
  },
  {
    icon: '🧋',
    name: '茶饮咖啡原料',
    description: '服务奶茶店、咖啡店连锁门店的原料补货',
    tags: ['连锁管理', '糖度识别', '配方同步', '多店汇总']
  },
  {
    icon: '✈️',
    name: '旅行社',
    description: '支持旅游线路智能解析、报名管理和群消息自动回复',
    tags: ['线路解析', '自动回复', '报名管理', '日报统计']
  },
  {
    icon: '🏗️',
    name: '工地管理',
    description: '支持工人考勤、工期管理、工程量统计和安全检查',
    tags: ['工人打卡', '天气关联', '安全检查', '质量管控']
  },
  {
    icon: '📚',
    name: '教育培训',
    description: '支持课程管理、学员跟踪、AI学习助手和学习进度分析',
    tags: ['AI学习助手', '学习进度', '智能批改', '个性化推荐']
  },
  {
    icon: '🏠',
    name: '房产中介',
    description: '支持房源管理、客户管理、智能推荐和交易流程跟踪',
    tags: ['智能推荐', '客户分析', '交易跟踪', '数据分析']
  },
  {
    icon: '🍱',
    name: '日料寿司',
    description: '专为日料店设计，支持海鲜类、寿司材料、调料类智能识别',
    tags: ['海鲜识别', '寿司套餐', '进口食材', '库存管理']
  },
  {
    icon: '🍞',
    name: '烘焙甜品',
    description: '支持面粉、黄油、奶油、糖类等烘焙原料识别和品牌备注',
    tags: ['品牌识别', '原料分类', '消耗分析', '效期管理']
  },
  {
    icon: '🏍️',
    name: '配件批发',
    description: '支持配件型号俗称、品牌代码和维修店快速下单',
    tags: ['型号识别', '配件俗称', '维修店模式', '配送统计']
  },
  {
    icon: '🚛',
    name: '车队调度',
    description: '支持车辆管理、任务调度、路线规划和运输跟踪',
    tags: ['实时监控', '任务调度', '路线优化', '维护保养']
  },
  {
    icon: '🔧',
    name: '水电五金配送',
    description: '支持临时加单、改单、规格备注识别',
    tags: ['改单识别', '规格提取', '线路汇总', '增量下单']
  },
  {
    icon: '⚡',
    name: '电动车配件配送',
    description: '支持电池、控制器、轮毂、电机等配件识别',
    tags: ['大件区分', '配件识别', '运输提示', '尺寸备注']
  },
  {
    icon: '📱',
    name: '手机零配件配送',
    description: '支持型号快速识别、图片文字备注解析',
    tags: ['型号识别', '配件图片备注', '维修店订单', '批量配单']
  }
]
</script>

<style scoped>
.industry-cases-page {
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

.cases {
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

.case-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 35px;
}

.case-card {
  background: #fff;
  border-radius: 24px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  transition: all 0.4s;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.case-card:hover {
  transform: translateY(-12px);
  box-shadow: 0 20px 50px rgba(99, 102, 241, 0.12);
  border-color: #6366f1;
}

.case-header {
  padding: 35px;
  background: #0f172a;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.case-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%);
}

.case-header-content {
  position: relative;
  z-index: 1;
}

.case-header h3 {
  font-size: 24px;
  margin-bottom: 8px;
}

.case-header .industry-tag {
  display: inline-block;
  background: rgba(255, 255, 255, 0.15);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  margin-top: 10px;
}

.case-body {
  padding: 35px;
}

.case-problem {
  margin-bottom: 25px;
}

.case-problem h4 {
  color: #ef4444;
  margin-bottom: 12px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.case-problem p {
  color: #64748b;
  font-size: 15px;
  line-height: 1.8;
}

.case-solution {
  margin-bottom: 25px;
}

.case-solution h4 {
  color: #6366f1;
  margin-bottom: 12px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.case-solution p {
  color: #64748b;
  font-size: 15px;
  line-height: 1.8;
}

.case-results {
  background: #f8fafc;
  padding: 25px;
  border-radius: 16px;
  margin-top: 25px;
}

.case-results h4 {
  color: #6366f1;
  margin-bottom: 20px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
  align-items: center;
}

.result-item:last-child {
  border-bottom: none;
}

.result-label {
  color: #64748b;
  font-size: 14px;
}

.result-value {
  color: #10b981;
  font-weight: 700;
  font-size: 16px;
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

.industries-preview {
  padding: 120px 20px;
  background: #f8fafc;
}

.industries-grid {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 30px;
}

.industry-card {
  display: flex;
  gap: 24px;
  padding: 35px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #e2e8f0;
  transition: all 0.4s;
}

.industry-card:hover {
  box-shadow: 0 15px 40px rgba(99, 102, 241, 0.1);
  transform: translateY(-8px);
  border-color: #6366f1;
}

.industry-icon {
  width: 70px;
  height: 70px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  flex-shrink: 0;
  transition: all 0.3s;
}

.industry-card:hover .industry-icon {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  transform: scale(1.1);
}

.industry-content h3 {
  font-size: 22px;
  color: #0f172a;
  margin-bottom: 12px;
  font-weight: 700;
}

.industry-content p {
  color: #64748b;
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 18px;
}

.industry-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.industry-tag {
  font-size: 13px;
  padding: 6px 14px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 20px;
  color: #475569;
  transition: all 0.3s;
}

.industry-card:hover .industry-tag {
  background: rgba(99, 102, 241, 0.1);
  border-color: #6366f1;
  color: #6366f1;
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

  .case-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .stat-number {
    font-size: 32px;
  }

  .industries-grid {
    grid-template-columns: 1fr;
  }
}
</style>