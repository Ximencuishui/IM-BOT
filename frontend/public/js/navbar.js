(function() {
    const NAV_CONFIG = {
        index: {
            links: [
                { href: '#features', text: '核心能力' },
                { href: '#demo-section', text: '在线演示' },
                { href: 'industries.html', text: '行业方案' },
                { href: 'cases.html', text: '客户案例' },
                { href: '#download', text: '下载中心' },
                { href: 'settings.html', text: '控制台' }
            ],
            activePage: 'index'
        },
        industries: {
            links: [
                { href: 'index.html#features', text: '核心能力' },
                { href: 'index.html#demo-section', text: '在线演示' },
                { href: 'industries.html', text: '行业方案', active: true },
                { href: 'cases.html', text: '客户案例' },
                { href: 'index.html#download', text: '下载中心' },
                { href: 'settings.html', text: '控制台' }
            ],
            activePage: 'industries'
        },
        cases: {
            links: [
                { href: 'index.html#features', text: '核心能力' },
                { href: 'index.html#demo-section', text: '在线演示' },
                { href: 'industries.html', text: '行业方案' },
                { href: 'cases.html', text: '客户案例', active: true },
                { href: 'index.html#download', text: '下载中心' },
                { href: 'settings.html', text: '控制台' }
            ],
            activePage: 'cases'
        },
        settings: {
            links: [
                { href: 'index.html#features', text: '核心能力' },
                { href: 'index.html#demo-section', text: '在线演示' },
                { href: 'industries.html', text: '行业方案' },
                { href: 'cases.html', text: '客户案例' },
                { href: 'index.html#download', text: '下载中心' },
                { href: 'settings.html', text: '控制台', active: true }
            ],
            activePage: 'settings'
        },
        setup: {
            links: [
                { href: 'index.html#features', text: '核心能力' },
                { href: 'index.html#demo-section', text: '在线演示' },
                { href: 'industries.html', text: '行业方案' },
                { href: 'cases.html', text: '客户案例' },
                { href: 'index.html#download', text: '下载中心' },
                { href: 'settings.html', text: '控制台' }
            ],
            activePage: 'setup'
        }
    };

    function generateNavbar(config) {
        const logoImage = './public/images/logo.png';
        const logoAlt = 'AI IMBot Logo';
        const logoStyle = 'height: 32px; margin-right: 8px;';
        
        let linksHtml = config.links.map(link => {
            const activeClass = link.active ? ' class="active"' : '';
            return `<li><a href="${link.href}"${activeClass}>${link.text}</a></li>`;
        }).join('\n');
        
        return `
        <nav class="navbar">
            <div class="nav-container">
                <a href="index.html" class="logo">
                    <img src="${logoImage}" alt="${logoAlt}" style="${logoStyle}"> AI IMBot
                </a>
                <ul class="nav-links">
                    ${linksHtml}
                </ul>
                <div class="nav-buttons">
                    <el-button onclick="window.location.href='index.html#download'" style="border-radius: 20px;">下载</el-button>
                    <el-button type="primary" onclick="window.location.href='settings.html'" style="border-radius: 20px;">登录控制台</el-button>
                </div>
                <button class="mobile-menu-btn" onclick="toggleMobileMenu()">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
            </div>
            <div class="mobile-menu">
                <ul class="mobile-nav-links">
                    ${linksHtml}
                </ul>
                <div class="mobile-buttons">
                    <el-button onclick="window.location.href='index.html#download'; toggleMobileMenu()" style="border-radius: 20px; width: 100%; margin-bottom: 10px;">下载</el-button>
                    <el-button type="primary" onclick="window.location.href='settings.html'; toggleMobileMenu()" style="border-radius: 20px; width: 100%;">登录控制台</el-button>
                </div>
            </div>
        </nav>
        `;
    }

    function initNavbar() {
        const navbarContainer = document.getElementById('navbar');
        if (!navbarContainer) return;
        
        const pageType = navbarContainer.getAttribute('data-page') || 'index';
        const config = NAV_CONFIG[pageType];
        
        if (!config) {
            console.error(`Navbar config not found for page: ${pageType}`);
            return;
        }
        
        navbarContainer.innerHTML = generateNavbar(config);
        
        window.addEventListener('scroll', function() {
            const navbar = document.querySelector('.navbar');
            if (navbar) {
                if (window.scrollY > 50) {
                    navbar.classList.add('scrolled');
                } else {
                    navbar.classList.remove('scrolled');
                }
            }
        });
    }

    function toggleMobileMenu() {
        const mobileMenu = document.querySelector('.mobile-menu');
        const mobileBtn = document.querySelector('.mobile-menu-btn');
        if (mobileMenu) {
            mobileMenu.classList.toggle('active');
        }
        if (mobileBtn) {
            mobileBtn.classList.toggle('active');
        }
    }

    function closeMobileMenu() {
        const mobileMenu = document.querySelector('.mobile-menu');
        const mobileBtn = document.querySelector('.mobile-menu-btn');
        if (mobileMenu) {
            mobileMenu.classList.remove('active');
        }
        if (mobileBtn) {
            mobileBtn.classList.remove('active');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNavbar);
    } else {
        initNavbar();
    }
})();