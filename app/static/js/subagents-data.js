/*
 * 板插板校核智能体配置
 * 单智能体版本：仅保留一个「板插板校核智能体」
 */
(function () {
    'use strict';

    const CAP = {
        DOC: '文档：文档生成与解析',
        DATA: '数据：数据分析与可视化',
        KB: '知识库：知识沉淀与问答',
        SEARCH: '检索：联网检索',
        DASHBOARD: '看板：网页看板生成',
        EMAIL: '邮件：邮件收发',
        AUTOMATION: '自动化：定时任务与提醒',
        FEISHU: '协同：飞书（规划中）'
    };

    function buildSubagents(workspaceId, rows) {
        return rows.map(function (row, index) {
            return {
                id: workspaceId + '-sub-' + String(index + 1).padStart(2, '0'),
                name: row[0],
                desc: row[1],
                capabilities: row[2]
            };
        });
    }

    const workspaces = {
        'failure-mode-analysis-agent': {
            name: '板插板校核智能体',
            icon: '📐',
            color: '#d4380d',
            slogan: '板插缺陷，智能识别',
            desc: '面向板插板结构的缺陷检查：用户上传板材的 2D 图片，智能体自动分析图片内容，识别板插板的设计缺陷并输出分析结论与改进建议。',
            subagents: buildSubagents('failure-mode-analysis-agent', [
                ['板插板校核智能体', '用户上传板材 2D 图片后，智能体分析图片中的板插板结构，识别设计缺陷（尺寸配合、干涉、结构强度、装配性等），输出缺陷分析结论、风险等级与改进建议。', [CAP.DOC, CAP.DATA, CAP.KB]]
            ])
        }
    };

    const subagentIndex = {};
    Object.keys(workspaces).forEach(function (workspaceId) {
        const workspace = workspaces[workspaceId];
        workspace.id = workspaceId;
        workspace.subagents.forEach(function (subagent) {
            subagent.workspaceId = workspaceId;
            subagent.workspaceName = workspace.name;
            subagentIndex[subagent.id] = subagent;
        });
    });

    window.SUBAO_WORKSPACE_CONFIG = workspaces;
    window.SUBAO_SUBAGENT_INDEX = subagentIndex;
    window.SUBAO_WORK_METHOD = {
        phaseOne: '以导入智能体知识库、数据分析与可视化导出为主要工作方式；知识库尽可能汇集公司及行业专业文件，例如体系文件、报告、缺陷案例和标准条款，形成公司级内部记忆。',
        phaseTwo: [
            '与 MES、QMS、ERP 等系统集成，可通过 MCP 或 API 扩展，后续升级为自动读取系统数据。',
            '实时在线 SPC 监控，需要直连 PLC 或 MES 数据流。',
            '机器视觉或 AI 外观检测，需要相机硬件与边缘推理部署。',
            '测量设备数据自动采集（三坐标、扭矩枪、气密仪直连），需要配套电子化设备。'
        ]
    };
})();
