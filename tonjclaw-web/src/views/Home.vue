<template>
  <div class="home-page">
    <nav class="navbar">
      <div class="nav-container">
        <div class="nav-logo">
          <span class="logo-text">AI <span class="logo-highlight">IMBot</span></span>
        </div>
        <div class="nav-links">
          <a href="#features" class="nav-link">核心能力</a>
          <a href="#platforms" class="nav-link">支持平台</a>
          <a href="/industry-cases" class="nav-link">行业案例</a>
          <a href="/plugin-store" class="nav-link">插件商店</a>
          <a href="/commercial-im" class="nav-link">商用IM</a>
        </div>
        <div class="nav-actions">
          <el-button text @click="goToLogin">登录</el-button>
          <el-button type="primary" @click="goToLogin">免费试用</el-button>
        </div>
      </div>
    </nav>

    <section class="hero">
      <div class="hero-content">
        <div class="logo">AI <span>IMBot</span></div>
        <h1>AI驱动的<span>桌面机器人</span>工具</h1>
        <p>智能解析IM消息，自动生成订单报表，支持飞书、钉钉等多平台接入，数据完全私有部署</p>
        <div class="hero-tags">
          <span class="hero-tag">🤖 AI智能解析</span>
          <span class="hero-tag">🔒 数据完全私有</span>
          <span class="hero-tag">💬 多平台IM支持</span>
          <span class="hero-tag">📊 自动化报表</span>
          <span class="hero-tag">⚡ 本地离线运行</span>
        </div>
        <div class="hero-buttons">
          <el-button size="large" type="primary" @click="scrollToDownload" style="font-weight: 600; padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><Download /></el-icon> 立即免费试用
          </el-button>
          <el-button size="large" plain @click="scrollToDemo" style="padding: 14px 40px; font-size: 16px; border-radius: 24px;">
            <el-icon><VideoPlay /></el-icon> 观看演示
          </el-button>
        </div>
      </div>
    </section>

    <section id="features" class="features">
      <h2 class="section-title">核心能力</h2>
      <p class="section-subtitle">AI IMBot 以本地化部署为核心，结合大模型AI、智能解析、规则引擎与自动报表，打造企业级IM自动化解决方案</p>
      <div class="feature-grid">
        <div class="feature-card">
          <div class="feature-icon">💬</div>
          <h3>多平台IM消息捕获</h3>
          <p>支持飞书、钉钉等主流IM平台的消息接入，实时捕获群组消息。无需转发，无需额外账号，彻底解决人工录入遗漏问题。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🧠</div>
          <h3>AI驱动智能解析</h3>
          <p>AI智能解析自然语言订单，精准识别口语化表达和快捷码。支持批量语法，复杂订单一键拆解。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔐</div>
          <h3>企业级数据隐私</h3>
          <p>软件在您的本地电脑运行，所有订单、客户、财务数据均存储在本地，绝不上传云端，确保商业机密安全。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>全自动多维度报表</h3>
          <p>定时生成Excel多Sheet报表，自动按线路、销售员、商品分类汇总。支持邮件自动推送。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🤖</div>
          <h3>智能交互机器人</h3>
          <p>可视化配置自动回复规则。客户发送"查订单"即可自助获取进度，大幅提升服务效率。</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚙️</div>
          <h3>灵活的规则引擎</h3>
          <p>支持解析规则与统计规则的动态配置。提供多格式导入导出，支持云端备份恢复。</p>
        </div>
      </div>
    </section>

    <section id="platforms" class="platforms">
      <h2 class="section-title">支持的平台</h2>
      <p class="section-subtitle">全面支持主流企业IM平台，为未来商用IM平台扩展预留接口</p>
      <div class="platforms-grid">
        <div class="platform-card">
          <div class="platform-icon">📧</div>
          <h3>飞书集成</h3>
          <p>通过飞书开放平台API实现消息监听和发送，支持飞书群聊和私聊消息接收。</p>
          <div class="platform-features">
            <div class="platform-feature"><el-icon><Check /></el-icon> 消息监听</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 消息卡片</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 用户信息</div>
          </div>
        </div>
        <div class="platform-card">
          <div class="platform-icon">💼</div>
          <h3>钉钉集成</h3>
          <p>通过钉钉开放平台API接入，支持钉钉机器人消息接收和发送，支持群聊和私聊。</p>
          <div class="platform-features">
            <div class="platform-feature"><el-icon><Check /></el-icon> 机器人消息</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 消息卡片</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 群管理</div>
          </div>
        </div>
        <div class="platform-card">
          <div class="platform-icon">🔮</div>
          <h3>通用IM接口</h3>
          <p>预留通用IM接入接口，支持自定义IM平台扩展。为未来开发自有商用IM平台做好技术准备。</p>
          <div class="platform-features">
            <div class="platform-feature"><el-icon><Check /></el-icon> 插件化设计</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 标准API</div>
            <div class="platform-feature"><el-icon><Check /></el-icon> 自定义扩展</div>
          </div>
        </div>
      </div>
    </section>

    <section class="stats-section">
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-number">10k+</div>
          <div class="stat-desc">日均处理订单数</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">99.8%</div>
          <div class="stat-desc">智能解析准确率</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">500+</div>
          <div class="stat-desc">活跃IM群组</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">24/7</div>
          <div class="stat-desc">全天候自动化运行</div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-content">
        <div class="footer-top">
          <div class="footer-brand">
            <h3>AI <span>IMBot</span></h3>
            <p>AI驱动的桌面机器人工具，让IM消息自动转化为清晰报表</p>
          </div>
          <div class="footer-links">
            <h4>产品</h4>
            <ul>
              <li><a href="#features">核心能力</a></li>
              <li><a href="#platforms">支持平台</a></li>
              <li><a href="/industry-cases">行业案例</a></li>
              <li><a href="/plugin-store">插件商店</a></li>
              <li><a href="/commercial-im">商用IM</a></li>
            </ul>
          </div>
          <div class="footer-links">
            <h4>支持</h4>
            <ul>
              <li><a href="#">帮助文档</a></li>
              <li><a href="#">常见问题</a></li>
              <li><a href="#">联系客服</a></li>
              <li><a href="#">反馈建议</a></li>
            </ul>
          </div>
          <div class="footer-links">
            <h4>关于</h4>
            <ul>
              <li><a href="#">公司介绍</a></li>
              <li><a href="#">隐私政策</a></li>
              <li><a href="#">服务条款</a></li>
              <li><a href="#">更新日志</a></li>
            </ul>
          </div>
        </div>
        <div class="footer-bottom">
          <p>© 2026 AI IMBot. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Check } from '@element-plus/icons-vue'

const router = useRouter()

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  font-family: var(--font-family);
  line-height: 1.6;
  color: var(--text-primary);
  overflow-x: hidden;
}

.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  padding: 14px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-logo .logo-text {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
}

.nav-logo .logo-highlight {
  background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  color: #e2e8f0;
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  transition: color 0.25s;
}

.nav-link:hover {
  color: #fff;
}

.nav-actions {
  display: flex;
  gap: 12px;
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

.hero h1 span {
  color: #a5b4fc;
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

.features {
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

.feature-grid {
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
}

.platforms {
  padding: 120px 20px;
  background: #0f172a;
  color: #fff;
}

.platforms .section-title {
  color: #fff;
}

.platforms .section-subtitle {
  color: #94a3b8;
}

.platforms-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 32px;
}

.platform-card {
  background: rgba(30, 41, 59, 0.6);
  padding: 40px;
  border-radius: 20px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s;
}

.platform-card:hover {
  background: rgba(30, 41, 59, 0.8);
  transform: translateY(-6px);
  border-color: rgba(99, 102, 241, 0.4);
}

.platform-icon {
  font-size: 52px;
  margin-bottom: 20px;
}

.platform-card h3 {
  font-size: 22px;
  margin-bottom: 12px;
  color: #fff;
  font-weight: 600;
}

.platform-card p {
  color: #94a3b8;
  font-size: 15px;
  line-height: 1.6;
}

.platform-features {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.platform-feature {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #e2e8f0;
  font-size: 14px;
}

.stats-section {
  padding: 80px 20px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
}

.stats-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 32px;
}

.stat-item {
  text-align: center;
  padding: 24px;
}

.stat-number {
  font-size: 48px;
  font-weight: 800;
  margin-bottom: 8px;
  letter-spacing: -1px;
}

.stat-desc {
  font-size: 15px;
  opacity: 0.9;
  font-weight: 500;
}

.footer {
  background: #020617;
  color: #94a3b8;
  padding: 80px 20px 32px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-top {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 48px;
  margin-bottom: 56px;
}

.footer-brand h3 {
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 16px;
}

.footer-brand h3 span {
  background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.footer-brand p {
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.footer-links h4 {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
}

.footer-links ul {
  list-style: none;
  padding: 0;
}

.footer-links li {
  margin-bottom: 10px;
}

.footer-links a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.25s;
}

.footer-links a:hover {
  color: #a5b4fc;
}

.footer-bottom {
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  text-align: center;
}

.footer-bottom p {
  font-size: 13px;
  color: #64748b;
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }
  
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
  
  .feature-grid {
    grid-template-columns: 1fr;
  }
  
  .platforms-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
  
  .stat-number {
    font-size: 32px;
  }
  
  .footer-top {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>