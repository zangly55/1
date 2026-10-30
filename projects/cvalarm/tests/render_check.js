// 用最小 DOM 桩执行报告页脚本：验证所有渲染函数都能跑通（无需浏览器）。
//
// 用法：node render_check.js <report.html>
// 退出码：0 = 通过；1 = 失败（会打印具体缺哪个面板/哪条断言）。
//
// 依赖仅为 node，属于"可选深度检查"：没有 node 时 test_render_js.py 会 skip，
// 纯 Python 的结构检查见 test_report_html.py。
'use strict';
const fs = require('fs');

const path = process.argv[2];
if (!path) { console.error('usage: node render_check.js <report.html>'); process.exit(1); }
const html = fs.readFileSync(path, 'utf8');

// ---------------------------------------------------------------- 解析页面
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (blocks.length < 3) { console.error('script blocks missing:', blocks.length); process.exit(1); }
const payloadMatch = blocks[0].match(/window\.__DATA__ = (\{[\s\S]*\});/);
if (!payloadMatch) { console.error('no embedded payload'); process.exit(1); }
const payload = JSON.parse(payloadMatch[1]);

// ---------------------------------------------------------------- 最小 DOM
const els = {};
function makeEl(id) {
  return {
    id, innerHTML: '', textContent: '', value: '',
    addEventListener() {},
    querySelector(sel) {
      const key = id + '::' + sel;
      if (!els[key]) els[key] = makeEl(key);
      return els[key];
    },
  };
}
let bootFn = null;
global.window = { __DATA__: null, __LIVE__: false };
global.document = {
  getElementById(id) { if (!els[id]) els[id] = makeEl(id); return els[id]; },
  addEventListener(ev, fn) { if (ev === 'DOMContentLoaded') bootFn = fn; },
};
global.fetch = async () => ({ ok: false });

// ---------------------------------------------------------------- 执行
let failures = [];
try {
  eval(blocks[2]);                       // 渲染脚本
} catch (e) {
  console.error('render script eval failed:', e.stack || e.message);
  process.exit(1);
}
if (!bootFn) { console.error('boot() not registered'); process.exit(1); }
global.window.__DATA__ = payload;
try {
  bootFn();
} catch (e) {
  console.error('boot() failed:', e.stack || e.message);
  process.exit(1);
}

// ---------------------------------------------------------------- 断言
// 每个面板都必须被真正写入内容（空字符串说明渲染函数没跑到或数据缺失）
const panels = ['hdr-sub', 'hdr-badge', 'kpis', 'funnel', 'funnel-prob', 'histogram',
  'loc-summary', 'loc-table::tbody', 'diff-summary', 'diff-table',
  'cost-table', 'topology-table::tbody', 'sensitivity', 'audit-summary',
  'audit-table::tbody', 'rules-meta', 'ledger-table::tbody',
  'res-summary', 'models-table::tbody', 'cap-table::tbody', 'proto-line',
  'notes', 'alarm-list', 'events-table::tbody', 'rel-table::tbody'];
for (const key of panels) {
  const el = els[key];
  const text = el ? (el.innerHTML + (el.textContent || '')) : '';
  if (!text) failures.push(`面板为空: ${key}`);
}
if (!(els['generated'] && els['generated'].textContent)) failures.push('生成时间未渲染');

const cards = (payload.alarms || []).filter(a => a.card);
const withEvidence = cards.filter(a => a.card.evidence && a.card.evidence.enabled);
const svgCount = ((els['alarm-list'] || {}).innerHTML || '').match(/<svg/g) || [];
if (withEvidence.length && svgCount.length < withEvidence.length) {
  failures.push(`证据示意图数量不足: ${svgCount.length} < ${withEvidence.length}`);
}
for (const a of withEvidence) {
  const ev = a.card.evidence;
  if (!ev.clip || typeof ev.clip.start !== 'number') failures.push(`${a.alarm_id} evidence.clip 缺失`);
  if (!Array.isArray(ev.keyframes) || !ev.keyframes.length) failures.push(`${a.alarm_id} keyframes 为空`);
  if (!a.card.provenance || !a.card.provenance.verifier) failures.push(`${a.alarm_id} provenance 缺失`);
}
const loc = (payload.metrics || {}).localization || {};
if (loc.per_event && loc.n !== loc.per_event.length) failures.push('localization.n 与 per_event 数量不一致');

if (failures.length) {
  console.error('RENDER: FAIL');
  for (const f of failures) console.error('  - ' + f);
  process.exit(1);
}
console.log(`RENDER: PASS（面板 ${panels.length} 个，卡片 ${cards.length} 张，证据示意图 ${withEvidence.length} 组）`);
process.exit(0);
