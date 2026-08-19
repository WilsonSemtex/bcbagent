/*
 * 失效模式分析智能体配置
 * 单智能体版本：仅保留一个「失效模式分析」智能体
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
            name: '失效模式分析',
            icon: '🔍',
            color: '#d4380d',
            slogan: '失效归因，闭环改进',
            desc: '面向产品失效模式与影响分析（FMEA）、失效根因分析与改进闭环，提供失效模式梳理、失效机理分析、风险优先级评估、8D 改进与防再发措施跟踪。',
            subagents: buildSubagents('failure-mode-analysis-agent', [
                ['失效模式分析', '梳理产品/过程失效模式与失效机理，评估严重度、发生频度与探测度（S/O/D），输出 RPN 风险排序与 FMEA 表格；支持 8D 失效根因分析、改进措施制定与防再发跟踪。', [CAP.DOC, CAP.DATA, CAP.KB]]
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
        phaseOne: '以导入智能体知识库、数据分析与可视化导出为主要工作方式；知识库尽可能汇集公司及行业专业文件，例如体系文件、报告、失效模式库和标准条款，形成公司级内部记忆。',
        phaseTwo: [
            '与 MES、QMS、ERP 等系统集成，可通过 MCP 或 API 扩展，后续升级为自动读取系统数据。',
            '实时在线 SPC 监控，需要直连 PLC 或 MES 数据流。',
            '机器视觉或 AI 外观检测，需要相机硬件与边缘推理部署。',
            '测量设备数据自动采集（三坐标、扭矩枪、气密仪直连），需要配套电子化设备。'
        ]
    };
})();
