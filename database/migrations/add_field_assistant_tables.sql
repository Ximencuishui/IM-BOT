-- 平场工程队现场管理助手系统 - 数据库迁移脚本
-- 创建7大模块所需的新表结构

-- 1. 工地信息表
CREATE TABLE IF NOT EXISTS t_field_site (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name VARCHAR(200) NOT NULL COMMENT '工地名称',
    location VARCHAR(500) COMMENT '工地位置',
    contract_no VARCHAR(100) UNIQUE COMMENT '合同编号',
    contract_unit_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '合同单价',
    contract_total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '合作总额',
    contract_total_volume DECIMAL(12,2) DEFAULT 0.00 COMMENT '合同总工程量',
    forecast_volume DECIMAL(12,2) DEFAULT 0.00 COMMENT '预测工程量',
    start_date DATE COMMENT '开工日期',
    end_date DATE COMMENT '竣工日期',
    status VARCHAR(20) DEFAULT 'in_progress' COMMENT '状态：in_progress/stopped/completed',
    remark VARCHAR(1000) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- 2. 员工薪资表
CREATE TABLE IF NOT EXISTS t_field_worker_salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL COMMENT '工人ID',
    salary_standard DECIMAL(10,2) NOT NULL COMMENT '工资标准',
    salary_type VARCHAR(20) DEFAULT 'daily' COMMENT '工资类型：daily/weekly/monthly/piecework',
    position VARCHAR(100) COMMENT '岗位',
    join_date DATE NOT NULL COMMENT '入职日期',
    leave_date DATE COMMENT '离职日期',
    site_id INTEGER COMMENT '所属工地ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (worker_id) REFERENCES t_construction_worker(id),
    FOREIGN KEY (site_id) REFERENCES t_field_site(id)
);

-- 3. 薪资计算表
CREATE TABLE IF NOT EXISTS t_field_salary_calc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL COMMENT '工人ID',
    calc_period VARCHAR(20) NOT NULL COMMENT '计算周期：weekly/monthly/quarterly',
    period_start DATE NOT NULL COMMENT '周期开始日期',
    period_end DATE NOT NULL COMMENT '周期结束日期',
    base_salary DECIMAL(10,2) DEFAULT 0.00 COMMENT '基础工资',
    overtime_salary DECIMAL(10,2) DEFAULT 0.00 COMMENT '加班工资',
    leave_deduction DECIMAL(10,2) DEFAULT 0.00 COMMENT '请假扣款',
    piecework_salary DECIMAL(10,2) DEFAULT 0.00 COMMENT '计件工资',
    total_salary DECIMAL(10,2) DEFAULT 0.00 COMMENT '应发工资',
    paid_status VARCHAR(20) DEFAULT 'unpaid' COMMENT '发放状态：unpaid/paid',
    paid_date DATE COMMENT '发放日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (worker_id) REFERENCES t_construction_worker(id)
);

-- 4. 计划工程量表
CREATE TABLE IF NOT EXISTS t_field_plan_volume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL COMMENT '工地ID',
    work_type VARCHAR(50) NOT NULL COMMENT '施工类型：earthwork_excavation/earthwork_backfill/land_leveling/compaction',
    period_type VARCHAR(20) DEFAULT 'daily' COMMENT '周期类型：daily/weekly/monthly',
    period_start DATE NOT NULL COMMENT '周期开始日期',
    period_end DATE COMMENT '周期结束日期',
    plan_volume DECIMAL(12,2) NOT NULL COMMENT '计划工程量',
    unit VARCHAR(20) NOT NULL COMMENT '单位：方/吨',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (site_id) REFERENCES t_field_site(id)
);

-- 5. 每日工程量表
CREATE TABLE IF NOT EXISTS t_field_daily_volume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL COMMENT '工地ID',
    work_type VARCHAR(50) NOT NULL COMMENT '施工类型',
    work_date DATE NOT NULL COMMENT '施工日期',
    actual_volume DECIMAL(12,2) NOT NULL COMMENT '实际工程量',
    unit VARCHAR(20) NOT NULL COMMENT '单位',
    reporter_id INTEGER COMMENT '上报人ID',
    remark VARCHAR(500) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (site_id) REFERENCES t_field_site(id),
    FOREIGN KEY (reporter_id) REFERENCES t_construction_worker(id)
);

-- 6. 费用科目表
CREATE TABLE IF NOT EXISTS t_field_expense_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name VARCHAR(100) NOT NULL COMMENT '科目名称',
    category_code VARCHAR(50) UNIQUE COMMENT '科目编码',
    parent_id INTEGER COMMENT '父科目ID',
    sort_order INTEGER DEFAULT 0 COMMENT '排序',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (parent_id) REFERENCES t_field_expense_category(id)
);

-- 7. 费用记录表
CREATE TABLE IF NOT EXISTS t_field_expense_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL COMMENT '工地ID',
    category_id INTEGER NOT NULL COMMENT '科目ID',
    amount DECIMAL(10,2) NOT NULL COMMENT '金额',
    expense_date DATE NOT NULL COMMENT '费用日期',
    reporter_id INTEGER COMMENT '上报人ID',
    remark VARCHAR(1000) COMMENT '备注',
    receipt_image VARCHAR(500) COMMENT '凭证图片路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (site_id) REFERENCES t_field_site(id),
    FOREIGN KEY (category_id) REFERENCES t_field_expense_category(id),
    FOREIGN KEY (reporter_id) REFERENCES t_construction_worker(id)
);

-- 8. 耗材表
CREATE TABLE IF NOT EXISTS t_field_consumable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_name VARCHAR(200) NOT NULL COMMENT '耗材名称',
    consumable_type VARCHAR(50) COMMENT '耗材类型：fuel/oil/spare_parts/tools/office_supplies/other',
    spec VARCHAR(200) COMMENT '规格型号',
    unit VARCHAR(20) NOT NULL COMMENT '单位：升/个/件/米/公斤',
    stock DECIMAL(10,2) DEFAULT 0.00 COMMENT '当前库存',
    min_stock DECIMAL(10,2) DEFAULT 0.00 COMMENT '库存阈值',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态：active/inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
);

-- 9. 耗材出入库记录表
CREATE TABLE IF NOT EXISTS t_field_consumable_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_id INTEGER NOT NULL COMMENT '耗材ID',
    site_id INTEGER NOT NULL COMMENT '工地ID',
    record_type VARCHAR(20) NOT NULL COMMENT '记录类型：in/out',
    quantity DECIMAL(10,2) NOT NULL COMMENT '数量',
    operator_id INTEGER COMMENT '操作人ID',
    remark VARCHAR(500) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (consumable_id) REFERENCES t_field_consumable(id),
    FOREIGN KEY (site_id) REFERENCES t_field_site(id),
    FOREIGN KEY (operator_id) REFERENCES t_construction_worker(id)
);

-- 10. 设备租赁表
CREATE TABLE IF NOT EXISTS t_field_equipment_lease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_name VARCHAR(200) NOT NULL COMMENT '设备名称',
    equipment_type VARCHAR(50) COMMENT '设备类型：excavator/loader/roller/truck/other',
    equipment_no VARCHAR(100) COMMENT '设备编号',
    site_id INTEGER NOT NULL COMMENT '租赁工地ID',
    lessor VARCHAR(200) COMMENT '出租方',
    lease_start_date DATE NOT NULL COMMENT '租赁开始日期',
    lease_end_date DATE NOT NULL COMMENT '租赁结束日期',
    lease_unit_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '租赁单价',
    lease_total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '租赁总费用',
    paid_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '已付费用',
    unpaid_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '未付费用',
    status VARCHAR(20) DEFAULT 'leasing' COMMENT '状态：leasing/returned/overdue',
    remark VARCHAR(1000) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (site_id) REFERENCES t_field_site(id)
);

-- 11. 财务记录表
CREATE TABLE IF NOT EXISTS t_field_financial_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type VARCHAR(20) NOT NULL COMMENT '收支类型：income/expense',
    income_source VARCHAR(50) COMMENT '收入来源：project_payment/other_income',
    expense_category VARCHAR(50) COMMENT '支出类别：salary/expense/reimbursement/purchase/lease/other',
    amount DECIMAL(12,2) NOT NULL COMMENT '金额',
    record_date DATE NOT NULL COMMENT '发生日期',
    site_id INTEGER COMMENT '所属工地ID',
    contract_no VARCHAR(100) COMMENT '关联合同编号',
    receivable_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '应收金额',
    received_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '已收金额',
    unpaid_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '未收金额',
    overdue_days INTEGER DEFAULT 0 COMMENT '逾期天数',
    remark VARCHAR(1000) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (site_id) REFERENCES t_field_site(id)
);

-- 12. 消息指令表
CREATE TABLE IF NOT EXISTS t_field_message_instruction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instruction_type VARCHAR(50) NOT NULL COMMENT '指令类型：site/worker/work_volume/expense/consumable/lease/finance',
    keyword VARCHAR(100) NOT NULL COMMENT '指令关键词',
    template VARCHAR(500) COMMENT '指令模板',
    description VARCHAR(500) COMMENT '指令说明',
    enabled TINYINT DEFAULT 1 COMMENT '是否启用：1=启用，0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- 13. 操作日志表
CREATE TABLE IF NOT EXISTS t_field_operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id INTEGER COMMENT '操作人ID',
    operator_name VARCHAR(100) COMMENT '操作人姓名',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型：create/update/delete/query',
    operation_object VARCHAR(200) COMMENT '操作对象',
    operation_content VARCHAR(1000) COMMENT '操作内容',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (operator_id) REFERENCES t_construction_worker(id)
);

-- 插入预设费用科目数据
INSERT INTO t_field_expense_category (category_name, category_code, parent_id, sort_order) VALUES
('燃油费', 'FUEL', NULL, 1),
('过路费', 'TOLL', NULL, 2),
('维修费', 'MAINTENANCE', NULL, 3),
('生活补贴', 'LIVING_ALLOWANCE', NULL, 4),
('易耗品', 'CONSUMABLES', NULL, 5),
('其他', 'OTHER', NULL, 6);

-- 插入预设消息指令数据
INSERT INTO t_field_message_instruction (instruction_type, keyword, template, description, enabled) VALUES
('work_volume', '工程量', '工程量 [工地名称] [施工类型] [数量][单位]', '上报当日工程量', 1),
('expense', '费用', '费用 [科目] [金额]元 [日期] [备注]', '上报费用', 1),
('consumable', '入库', '入库 [耗材名称] [数量][单位] [工地]', '耗材入库', 1),
('consumable', '出库', '出库 [耗材名称] [数量][单位] [工地] [用途]', '耗材出库', 1),
('site', '工地', '工地 [列表/创建/详情]', '工地管理指令', 1),
('worker', '员工', '员工 [列表/新增/调薪]', '员工管理指令', 1),
('finance', '记账', '记账 [收入/支出] [金额]元 [备注]', '财务记账指令', 1),
('report', '报表', '报表 [日报/周报/月报]', '报表查询指令', 1);