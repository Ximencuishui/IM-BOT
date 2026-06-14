(function() {
    function generateFooter() {
        return `
        <footer class="footer">
            <div class="footer-content">
                <div class="footer-top">
                    <div class="footer-brand">
                        <h3>AI <span>IMBot</span></h3>
                        <p>AI驱动的桌面机器人工具，智能解析IM消息，自动生成订单报表，支持飞书、钉钉等多平台接入。</p>
                    </div>
                    <div class="footer-links">
                        <h4>产品</h4>
                        <ul>
                            <li><a href="index.html#features">核心能力</a></li>
                            <li><a href="index.html#demo-section">在线演示</a></li>
                            <li><a href="index.html#download">下载中心</a></li>
                            <li><a href="industries.html">行业方案</a></li>
                        </ul>
                    </div>
                    <div class="footer-links">
                        <h4>资源</h4>
                        <ul>
                            <li><a href="cases.html">客户案例</a></li>
                            <li><a href="#">开发文档</a></li>
                            <li><a href="#">API参考</a></li>
                            <li><a href="#">更新日志</a></li>
                        </ul>
                    </div>
                    <div class="footer-links">
                        <h4>公司</h4>
                        <ul>
                            <li><a href="#">关于我们</a></li>
                            <li><a href="#">联系我们</a></li>
                            <li><a href="#">加入我们</a></li>
                            <li><a href="#">合作伙伴</a></li>
                        </ul>
                    </div>
                </div>
                <div class="footer-bottom">
                    <p>&copy; 2026 AI IMBot. All rights reserved. | <a href="#" style="color: #64748b;">隐私政策</a> | <a href="#" style="color: #64748b;">服务条款</a></p>
                </div>
            </div>
        </footer>
        `;
    }

    function initFooter() {
        const footerContainer = document.getElementById('footer');
        if (!footerContainer) return;
        
        footerContainer.innerHTML = generateFooter();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFooter);
    } else {
        initFooter();
    }
})();