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
            color: '#1051BF',
            slogan: '智能识别板插板缺陷',
            desc: '面向板插板结构的缺陷检查：用户上传板材的.DXF文件，智能体自动分析图纸内容，识别板插板的设计缺陷并输出分析结论与改进建议。',
            subagents: buildSubagents('failure-mode-analysis-agent', [
                ['板插板校核智能体', '用户上传板材.DXF文件后，智能体分析图片中的板插板结构，识别设计缺陷（配合、干涉、装配性等），输出缺陷分析结论、风险等级与改进建议。', [CAP.DOC, CAP.DATA, CAP.KB]]
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
        phaseOne: '以导入智能体知识库、现有案例分析与对话导出为主要工作方式；知识库尽可能收集常见绘制错误案例，形成团队经验库。',
        phaseTwo: [
            '1.输出缺陷位置并在图中标出。（未上线）',
            '2.给出缺陷评价与修改意见。（未上线）',
            '3.对整批板插板库进行自动排版，输出可直接雕刻的g代码。（未上线）'
        ]
    };
})();
