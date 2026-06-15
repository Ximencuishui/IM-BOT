<template>
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
            <li><router-link to="/">首页</router-link></li>
            <li><router-link to="/industry-cases">行业案例</router-link></li>
            <li><router-link to="/plugin-store">插件商店</router-link></li>
            <li><router-link to="/commercial-im">商用IM</router-link></li>
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
</template>

<script setup>
</script>

<style scoped>
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

.footer-links a,
.footer-links router-link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.25s;
}

.footer-links a:hover,
.footer-links router-link:hover {
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
  .footer-top {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>