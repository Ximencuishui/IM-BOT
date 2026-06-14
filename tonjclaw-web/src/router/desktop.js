const desktopRoutes = [
  {
    path: '/desktop',
    component: () => import('../layouts/DesktopLayout.vue'),
    meta: { requiresAuth: true },
    redirect: '/desktop/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'DesktopDashboard',
        component: () => import('../views/desktop/Dashboard/index.vue'),
        meta: { title: '数据概览' }
      },
      {
        path: 'orders',
        name: 'DesktopOrders',
        component: () => import('../views/desktop/Orders/index.vue'),
        meta: { title: '订单管理' }
      },
      {
        path: 'products',
        name: 'DesktopProducts',
        component: () => import('../views/desktop/Products/index.vue'),
        meta: { title: '商品管理' }
      },
      {
        path: 'salespersons',
        name: 'DesktopSalespersons',
        component: () => import('../views/desktop/Salespersons/index.vue'),
        meta: { title: '销售人员' }
      },
      {
        path: 'customers',
        name: 'DesktopCustomers',
        component: () => import('../views/desktop/Customers/index.vue'),
        meta: { title: '客户管理' }
      },
      {
        path: 'groups',
        name: 'DesktopGroups',
        component: () => import('../views/desktop/Groups/index.vue'),
        meta: { title: '群管理' }
      },
      {
        path: 'robot',
        name: 'DesktopRobot',
        component: () => import('../views/desktop/Robot/index.vue'),
        meta: { title: '机器人运行' }
      },
      {
        path: 'reports',
        name: 'DesktopReports',
        component: () => import('../views/desktop/Reports/index.vue'),
        meta: { title: '报表统计' }
      },
      {
        path: 'rules',
        name: 'DesktopRules',
        component: () => import('../views/desktop/Rules/index.vue'),
        meta: { title: '规则配置' }
      },
      {
        path: 'routes',
        name: 'DesktopRoutes',
        component: () => import('../views/desktop/Routes/index.vue'),
        meta: { title: '线路管理' }
      },
      {
        path: 'licenses',
        name: 'DesktopLicenses',
        component: () => import('../views/desktop/Licenses/index.vue'),
        meta: { title: '授权码管理' }
      },
      {
        path: 'ops',
        name: 'DesktopOps',
        component: () => import('../views/desktop/Ops/index.vue'),
        meta: { title: '系统运维' }
      }
    ]
  }
]

export default desktopRoutes
