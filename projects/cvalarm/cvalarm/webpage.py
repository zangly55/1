"""自包含 Web 页面：静态报告与实时看板共用同一套渲染逻辑。

不引用任何外部 CDN / 字体 / 图表库——监控系统常常跑在无外网的机房内，
报告必须能离线打开（论文 7.1 节"联网状态与合规性由配置决定"的工程推论）。
"""
from __future__ import annotations

import html
import json
from typing import Any, Optional


def _esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def build_payload(meta: dict, metrics: dict, cost: dict, reliability: dict, audit: dict,
                  alarms: list[dict], events: list[dict], histogram: dict,
                  rules: dict, ledger: list[dict], topologies: Optional[list[dict]] = None,
                  feedback: Optional[dict] = None, generated_at: str = "") -> dict:
    """裁剪掉重复的大字段，生成页面数据。"""
    slim_metrics = {k: v for k, v in metrics.items()
                    if k not in ("alarms_detail", "events_detail")}
    return {
        "meta": meta,
        "metrics": slim_metrics,
        "cost": cost,
        "reliability": reliability,
        "audit": audit,
        "alarms": alarms,
        "events": events,
        "histogram": histogram,
        "rules": rules,
        "ledger": ledger,
        "topologies": topologies or [],
        "feedback": feedback or {},
        "generated_at": generated_at,
    }


CSS = """
:root{
  --bg:#0d1117; --panel:#161b22; --panel2:#1c2330; --line:#2a3441;
  --fg:#e6edf3; --muted:#8b98a5; --accent:#4aa8ff; --ok:#3fb950;
  --warn:#d29922; --bad:#f85149; --peak:#a371f7;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
header{padding:22px 28px 16px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,#131a24,#0d1117)}
h1{margin:0 0 6px;font-size:21px;letter-spacing:.3px}
h2{margin:0 0 14px;font-size:16px;color:var(--fg)}
h3{margin:18px 0 8px;font-size:14px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.08em}
.sub{color:var(--muted);font-size:12.5px}
main{padding:20px 28px 60px;max-width:1400px;margin:0 auto}
.grid{display:grid;gap:14px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(168px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi .label{color:var(--muted);font-size:12px;letter-spacing:.02em}
.kpi .value{font-size:25px;font-weight:650;margin-top:4px;font-variant-numeric:tabular-nums}
.kpi .hint{color:var(--muted);font-size:11.5px;margin-top:2px}
.ok{color:var(--ok)} .warn{color:var(--warn)} .bad{color:var(--bad)} .accent{color:var(--accent)}
section{margin-top:26px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
tbody tr:hover{background:#1a2130}
code,.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;
  border:1px solid var(--line);background:var(--panel2)}
.pill.ok{border-color:#245c33;background:#12261a;color:var(--ok)}
.pill.warn{border-color:#5c4a12;background:#241f10;color:var(--warn)}
.pill.bad{border-color:#5c1f1f;background:#261212;color:var(--bad)}
.pill.info{border-color:#1f3d5c;background:#101e26;color:var(--accent)}
.bar{height:8px;border-radius:4px;background:#22303f;overflow:hidden}
.bar > i{display:block;height:100%;background:var(--accent)}
.funnel{display:flex;flex-direction:column;gap:8px}
.funnel .row{display:grid;grid-template-columns:190px 1fr 120px;gap:10px;align-items:center}
.funnel .track{background:#141b26;border:1px solid var(--line);border-radius:6px;height:26px;
  position:relative;overflow:hidden}
.funnel .fill{height:100%;background:linear-gradient(90deg,#1f6feb,#4aa8ff)}
.funnel .fill.warnc{background:linear-gradient(90deg,#7d5b00,#d29922)}
.funnel .fill.badc{background:linear-gradient(90deg,#7d1f1f,#f85149)}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;margin-bottom:10px}
details[open]{background:var(--panel2)}
summary{cursor:pointer;font-weight:600;outline:none}
.summary-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.kv{display:grid;grid-template-columns:170px 1fr;gap:4px 12px;margin:10px 0}
.kv .k{color:var(--muted)}
pre{background:#0b0f16;border:1px solid var(--line);border-radius:8px;padding:10px;
  overflow:auto;font-size:12px;max-height:340px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.split{grid-template-columns:1fr}
  .funnel .row{grid-template-columns:140px 1fr 90px}}
.note{border-left:3px solid var(--accent);background:#101820;padding:10px 14px;
  border-radius:0 8px 8px 0;color:var(--muted);font-size:12.5px;margin-top:10px}
.warn-note{border-left-color:var(--warn);background:#1a1710}
.bad-note{border-left-color:var(--bad);background:#1a1113}
footer{color:var(--muted);font-size:12px;padding:20px 28px;border-top:1px solid var(--line)}
.hm td{font-variant-numeric:tabular-nums}
.legend{display:flex;gap:14px;color:var(--muted);font-size:12px;margin-top:6px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
input[type=search]{background:#0b0f16;border:1px solid var(--line);color:var(--fg);
  padding:6px 10px;border-radius:7px;width:240px}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.badge-line{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;align-items:center}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:11.5px;
  border:1px solid var(--line);background:#101820;color:var(--muted)}
.badge.replay{border-color:#5c4a12;background:#1a1710;color:var(--warn)}
.badge.live{border-color:#245c33;background:#12261a;color:var(--ok)}
.evidence{border:1px solid var(--line);border-radius:8px;padding:10px;margin:10px 0;
  background:#0b0f16}
.evidence video{width:100%;max-height:320px;border-radius:6px;background:#000}
.evidence svg{display:block}
.kv2{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:8px 0}
.kv2 > div{background:#101820;border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.kv2 .lab{color:var(--muted);font-size:11.5px}
.kv2 .val{font-size:16px;font-weight:600;font-variant-numeric:tabular-nums}
.tag{font-size:11px;padding:1px 7px;border-radius:6px;background:#16202c;
  border:1px solid var(--line);color:var(--muted)}
"""

JS = r"""
let D = window.__DATA__ || {};
const $ = (id) => document.getElementById(id);
const fmt = (v, n = 2) => (v === null || v === undefined || Number.isNaN(v)) ? '-' : Number(v).toFixed(n);
const pct = (v, n = 1) => (v === null || v === undefined) ? '-' : (Number(v) * 100).toFixed(n) + '%';
const esc = (s) => String(s === null || s === undefined ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

function kpi(label, value, cls, hint) {
  return `<div class="card kpi"><div class="label">${esc(label)}</div>
    <div class="value ${cls||''}">${value}</div>
    <div class="hint">${esc(hint||'')}</div></div>`;
}

function renderHeader() {
  const m = D.meta || {}, r = (D.metrics || {}), rs = m.ruleset || {};
  $('hdr-sub').innerHTML =
    `运行 <code>${esc(m.run_id||'')}</code> · 帧数 ${esc(m.frames||0)} · ` +
    `可评价 ${esc((r.evaluable_video_hours||r.camera_hours||0))} 机位·小时 · ` +
    `时延口径 ${esc(m.latency_measurement_kind||'legacy-unverified')}（未测浏览器显示） · 处理耗时 ${esc(m.wall_seconds||0)}s (${esc(m.processing_fps||'-')} fps) · ` +
    `核验器 <code>${esc(m.verifier_mode||'')}</code> · ` +
    `规则集 <code>${esc(rs.version_label||'')}@${esc(rs.digest||'')}</code>`;
  const prov = m.provenance || {};
  const models = m.models || {};
  const mode = (m.protocol || {}).mode || 'none';
  const replayLive = String(prov.replay_mode || '').includes('live');
  const badges = [
    `<span class="badge ${replayLive ? 'live' : 'replay'}">${replayLive ? '现场推理' : '离线回放验证'}</span>`,
    `<span class="badge">数据来源：${esc(prov.data_source||'-')}</span>`,
    `<span class="badge">核验链路：${esc(prov.verifier||'-')}</span>`,
    `<span class="badge">检测：${esc((models.detector||{}).id||'-')}</span>`,
    `<span class="badge">定位打分头：${esc((models.localizer||{}).id||'-')}</span>`,
    `<span class="badge">评测协议：${mode === 'holdout' ? '开发/测试隔离' : '全量评测'}</span>`,
  ];
  if (prov.claim) badges.push(`<span class="sub">${esc(prov.claim)}</span>`);
  $('hdr-badge').innerHTML = badges.join('');
}

function renderKpis() {
  const r = D.metrics || {}, tta = r.tta || {}, ttae = r.tta_event_start || {},
        td = r.threshold_delay || {}, loc = r.localization || {}, c = D.cost || {};
  const costTotal = (c.components_money_per_camera_hour||{}).total;
  const aer = r.no_event_rejection || {};
  const cls = (v, good, bad) => v === null || v === undefined ? '' : (v >= good ? 'ok' : (v <= bad ? 'bad' : 'warn'));
  $('kpis').innerHTML = [
    kpi('事件级召回（仅确证）', pct(r.event_recall), cls(r.event_recall, .9, .5),
        `${r.event_tp_confirmed||0}/${r.events||0} 事件`),
    kpi('事件级召回（含转人工）', pct(r.event_recall_incl_deferred), cls(r.event_recall_incl_deferred, .95, .6),
        `${r.event_tp_displayed||0}/${r.events||0} 事件`),
    kpi('FA/CH 每机位小时误报', fmt(r.false_alarms_per_camera_hour, 3),
        (r.false_alarms_per_camera_hour <= .2 ? 'ok' : (r.false_alarms_per_camera_hour <= .5 ? 'warn' : 'bad')),
        `${r.false_alarms||0} 次合并误报 / ${r.camera_hours||0} 机位·小时`),
    kpi('告警时延 p50（阈值满足→告警）', tta.p50 === null || tta.p50 === undefined ? '-' : fmt(tta.p50,2)+'s',
        (tta.p50 !== undefined && tta.p50 <= 30 ? 'ok' : 'warn'),
        `p90 ${fmt(tta.p90,2)}s · 截止 ${fmt(tta.deadline_s,0)}s 内 ${pct(tta.deadline_recall)}`),
    kpi('告警时延 p50（事件起点→告警）', ttae.p50 === null || ttae.p50 === undefined ? '-' : fmt(ttae.p50,2)+'s',
        'accent', `p90 ${fmt(ttae.p90,2)}s · 含规程等待 ${fmt(td.p50,1)}s`),
    kpi('定位起点误差 MAE', loc.ref_start_mae_s === null || loc.ref_start_mae_s === undefined ? '-' : fmt(loc.ref_start_mae_s,2)+'s',
        (loc.ref_start_mae_s !== undefined && loc.ref_start_mae_s <= 5 ? 'ok' : 'warn'),
        `窗口内 mIoU ${fmt(loc.ref_miou_mean,3)} · 边界命中 ${pct(loc.ref_boundary_hit_rate)} · n=${loc.n||0}（raw MAE ${fmt(loc.start_mae_s,1)}s）`),
    kpi('帧级 ROC-AUC', fmt(r.frame_roc_auc, 3),
        (r.frame_roc_auc || 0) >= .85 ? 'ok' : ((r.frame_roc_auc||0) >= .7 ? 'warn':'bad'),
        '仅反映排序能力，不代表告警负担'),
    kpi('无事件静默抑制率', pct(aer.rejection_rate), aer.rejection_rate >= .8 ? 'ok':'warn',
        `${aer.silent||0}/${aer.windows||0} 抽样窗口 · 未决 ${aer.uncertain||0}`),
    kpi('全链路成本 / 机位·小时', costTotal === undefined ? '-' : fmt(costTotal, 4),
        'accent', `拓扑 ${esc(c.topology||'-')}`),
  ].join('');
}

function renderTriage() {
  const r = D.metrics || {}, tc = r.triage_counts || {}, st = D.stats || {};
  const frames = st.frames || 0, cands = st.candidates || 0;
  const eventN = tc.EVENT || 0, disp = (r.displayed_alarms||0), conf = (r.confirmed_alarms||0);
  const rows = [
    ['帧输入（Stage1 常驻）', frames, 'base', '每一帧都过轻量检测+跟踪+FSM'],
    ['Stage1 候选（触发粗窗口）', cands, 'ok', `候选视频 ${fmt(st.candidate_video_seconds,1)}s`],
    ['Stage2 判定存在性（EVENT）', eventN, 'ok', '非自回归区间打分 + Kadane 解码'],
    ['Stage3 显示到中控台', disp, 'warnc', '含存疑转人工卡片'],
    ['人工可确认的告警', conf, 'ok', '规程适用性判定为违规'],
    ['系统异常窗口（重检队列）', tc.SYSTEM_ERROR || 0, 'badc', '采集中断，不判定为正常'],
  ];
  const max = Math.max(1, frames);
  $('funnel').innerHTML = rows.map(([label, val, cls, hint]) => {
    const w = Math.max(val > 0 ? 1.2 : 0, (val / max) * 100);
    const c = cls === 'base' ? '' : (cls === 'warnc' ? 'warnc' : (cls === 'badc' ? 'badc' : ''));
    return `<div class="row"><div>${esc(label)}<div class="sub">${esc(hint)}</div></div>
      <div class="track"><div class="fill ${c}" style="width:${w}%"></div></div>
      <div class="mono" style="text-align:right">${val}</div></div>`;
  }).join('');
  const rel = D.reliability || {};
  $('funnel-prob').innerHTML = `
    <div class="kv">
      <div class="k">p1 前筛保留率</div><div class="mono">${fmt(rel.p1_prefilter,3)}</div>
      <div class="k">p2|1 定位保留率</div><div class="mono">${fmt(rel.p2_given_1_localizer,3)}</div>
      <div class="k">p3|1,2 复核确证率</div><div class="mono">${fmt(rel.p3_given_12_verifier,3)}</div>
      <div class="k">条件概率链乘积</div><div class="mono">${fmt(rel.conditional_chain_product ?? rel.p_total_independent_estimate,3)}</div>
      <div class="k">实测端到端召回</div><div class="mono accent">${fmt(rel.end_to_end_recall_observed,3)}
        <span class="sub">CI95 ${esc(JSON.stringify(rel.end_to_end_recall_ci95||[]))}</span></div>
      <div class="k">瓶颈环节</div><div class="mono warn">${esc(rel.bottleneck||'-')}</div>
    </div>
    <div class="note">${esc(rel.note||'')}</div>`;
}

function renderEvents() {
  const ev = D.events || [], pe = (D.metrics||{}).per_event || [];
  const byId = {}; pe.forEach(e => byId[e.event_id] = e);
  const pillOf = (s) => s === 'TP' ? 'ok' : (s === 'MISS' ? 'bad' : 'warn');
  $('events-table').querySelector('tbody').innerHTML = ev.map(e => {
    const m = byId[e.event_id] || {};
    const status = m.status === 'TP'
      ? `<span class="pill ok">TP · ${esc(m.alarm_status)}</span>`
      : `<span class="pill bad">未匹配告警</span>`;
    return `<tr><td class="mono">${esc(e.event_id)}</td><td>${esc(e.camera_id)}</td>
      <td class="mono">${esc(e.event_class)}</td>
      <td class="mono">${fmt(e.start,1)} → ${fmt(e.end,1)}</td>
      <td class="mono">${fmt(e.satisfy_ts || e.start,1)}</td>
      <td>${status}</td><td class="mono">${m.tta === undefined || m.tta === null ? '-' : fmt(m.tta,2)+'s'}</td>
      <td class="mono">${fmt(m.iou,3)}</td>
      <td class="sub">${esc(e.note||'')}</td></tr>`;
  }).join('');
}

function statusPill(s) {
  const map = {confirmed:'ok', deferred:'warn', suppressed:'info', system_error:'bad'};
  return `<span class="pill ${map[s]||''}">${esc(s)}</span>`;
}

function renderEvidenceBlock(card) {
  const ev = card.evidence || {};
  if (!ev.enabled) return '';
  const clip = ev.clip || {}, media = ev.media || {}, kfs = ev.keyframes || [];
  const video = media.available
    ? `<video controls preload="metadata" src="${esc(media.url_template)}#t=${fmt(clip.start,1)},${fmt(clip.end,1)}"></video>`
    : `<div class="sub">原片段回放需在 deployment.media.cameras 里登记视频文件；` +
      `当前展示由检测结果重绘的证据示意图与回放清单。</div>`;
  return `<div class="evidence">
    <div class="sub">证据回放：片段 [${fmt(clip.start,1)}, ${fmt(clip.end,1)}]s
      （前卷 ${fmt(clip.pre_roll_s,1)}s / 后卷 ${fmt(clip.post_roll_s,1)}s）·
      关键帧 ${kfs.length} 个 · 模式 ${esc(ev.replay_mode||'')}</div>
    ${video}${ev.schematic_svg||''}
    <div class="sub">${esc(ev.manifest||'')}</div></div>`;
}

function renderReview(a) {
  const entries = ((D.feedback||{}).entries||[]).filter(x => x.alarm_id === a.alarm_id);
  const last = entries.length ? entries[entries.length-1] : null;
  const history = last ? `<p>最近复核：${esc(last.verdict)} · ${esc(last.operator)} · ${esc(last.note||last.reason_code)}</p>` : '<p>尚未复核</p>';
  if (!window.__LIVE__) return history + '<p class="sub">静态报告只读；启动看板服务后可提交复核。</p>';
  if (!['confirmed','deferred'].includes(a.status)) return '';
  const options = ((D.feedback||{}).reason_codes||[]).map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  return history + `<form class="review-form" data-alarm="${esc(a.alarm_id)}">
    <label>复核人 <input name="operator" required value="operator"></label>
    <label>理由 <select name="reason_code"><option value="">请选择（驳回时必填）</option>${options}</select></label>
    <label>备注 <input name="note" maxlength="1000"></label>
    <button type="submit" name="verdict" value="confirm">确认</button>
    <button type="submit" name="verdict" value="dismiss">驳回</button>
    <button type="submit" name="verdict" value="uncertain">暂不判断</button>
    <span class="review-status" role="status"></span></form>`;
}

document.addEventListener('submit', async event => {
  const form = event.target;
  if (!form.classList.contains('review-form')) return;
  event.preventDefault();
  const status = form.querySelector('.review-status');
  const values = new FormData(form);
  const verdict = event.submitter && event.submitter.value;
  if (!verdict) return;
  if (verdict === 'dismiss' && !values.get('reason_code')) { status.textContent='请选择驳回理由'; return; }
  window.__REVIEW_BUSY__ = true;
  status.textContent='正在保存…';
  try {
    const resp = await fetch('/api/feedback', {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({run_id:D.meta.run_id,alarm_id:form.dataset.alarm,verdict,
        operator:values.get('operator'),reason_code:values.get('reason_code'),note:values.get('note')})});
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || '保存失败');
    D.feedback = D.feedback || {}; D.feedback.entries = (D.feedback.entries||[]).concat([data.entry]);
    status.textContent='已保存：'+data.entry.verdict;
  } catch(e) { status.textContent='保存失败：'+e.message; }
  finally { window.__REVIEW_BUSY__=false; }
});

function renderAlarms() {
  const alarms = D.alarms || [];
  const q = ($('alarm-search') && $('alarm-search').value || '').toLowerCase();
  const shown = alarms.filter(a => !q || JSON.stringify(a).toLowerCase().includes(q));
  $('alarm-list').innerHTML = shown.map((a, i) => {
    const card = a.card || {};
    const anchor = card.Temporal_Anchor || {};
    const norm = card.Normative_Inference_Uncertainty || {};
    const facts = card.Physical_Fact_Evidence || [];
    const lat = a.latency || {};
    const keyparts = Object.entries(lat).filter(([k]) => k.endsWith('_ms') && k !== 'total_ms')
      .map(([k,v]) => `${k.replace('_ms','')}=${fmt(v,1)}ms`).join(' · ');
    return `<details ${i<3?'open':''}><summary>
      <span class="summary-row">
        ${statusPill(a.status)}
        <code>${esc(a.alarm_id)}</code>
        <span class="pill">${esc(a.camera_id)} / ${esc(a.roi_id)}</span>
        <span class="pill">${esc(a.event_class)}</span>
        <span class="mono">触发 ${fmt(a.t_trigger,1)}s</span>
        <span class="mono">TTA ${fmt(a.t_display - a.t_satisfy,2)}s</span>
        <span class="mono">${esc(a.triage)}</span>
        ${card.decision ? `<span class="pill ${card.decision==='confirm'?'ok':(card.decision==='dismiss'?'info':'warn')}">${esc(card.decision)}</span>` : ''}
      </span></summary>
      ${a.suppression_reason ? `<div class="note warn-note">${esc(a.suppression_reason)}</div>` : ''}
      ${card.card_id ? `
        <div class="kv">
          <div class="k">时间锚点</div><div class="mono">[${fmt(anchor.start,2)}, ${fmt(anchor.end,2)}] s ·
            关键帧 ${esc((anchor.keyframes||[]).join(', '))} · 累计 ${fmt(anchor.dwell_seconds,1)}s</div>
          <div class="k">置信度</div><div class="mono">${fmt(card.confidence,3)}</div>
          <div class="k">规范依据</div><div>${esc(norm.norm_ref||'')}</div>
          <div class="k">判断依据</div><div>${esc(norm.basis||'')}</div>
          <div class="k">画面事实</div><div>${facts.map(f => `• ${esc(f.fact)} <span class="sub">[frame ${esc(f.frame)} · ${esc(f.source)}]</span>`).join('<br>')}</div>
          <div class="k">未决事项</div><div>${(norm.uncertainties||[]).map(u => `• ${esc(u)}`).join('<br>') || '—'}</div>
          <div class="k">时延分解</div><div class="mono">${esc(keyparts)} · 合计 ${fmt(lat.total_ms,0)}ms</div>
          <div class="k">双向上下文对照</div><div class="mono">因果左窗 ${fmt(lat.total_ms,0)}ms
            vs 等待片段闭合 ${fmt(lat.bidirectional_reference_ms,0)}ms</div>
          <div class="k">签名</div><div class="mono">${esc(card.signature||'未签名')}</div>
          <div class="k">溯源</div><div class="sub">${esc((card.provenance||{}).verifier||'')} ·
            ${esc((card.provenance||{}).data_source||'')} ·
            ${esc((card.provenance||{}).claim||'')}</div>
        </div>
        ${renderEvidenceBlock(card)}
        ${renderReview(a)}
        <pre>${esc(JSON.stringify({event_class:card.event_class,
          Temporal_Anchor:anchor, Physical_Fact_Evidence:facts,
          Normative_Inference_Uncertainty:norm}, null, 2))}</pre>`
      : `<div class="sub">无卡片（${esc(a.triage)}）：${esc(a.suppression_reason)}</div>`}
    </details>`;
  }).join('') || '<div class="sub">没有告警记录</div>';
}

function renderCost() {
  const c = D.cost || {}, g = c.components_gpu_seconds_per_camera_hour || {};
  const m = c.components_money_per_camera_hour || {}, r = c.ratios || {}, me = c.measured || {};
  const row = (k, v, cls='') => `<tr><td>${esc(k)}</td><td class="mono ${cls}" style="text-align:right">${v}</td></tr>`;
  $('cost-table').innerHTML = `
    <tr><th>项</th><th style="text-align:right">值</th></tr>
    ${row('C_always_on（Stage1 常驻，GPU·s/机位·小时）', fmt(g.C_always_on_stage1,2))}
    ${row('C2（每候选视频小时）', fmt(g.C2_per_candidate_video_hour,2))}
    ${row('r1 · C2', fmt(g.r1_times_C2,4))}
    ${row('C3（每第三级输入视频小时）', fmt(g.C3_per_input_video_hour,2))}
    ${row('r1 · r2 · C3', fmt(g.r1_r2_times_C3,4))}
    ${row('<b>合计 GPU·s / 机位·小时</b>', '<b>'+fmt(g.total_gpu_seconds,2)+'</b>')}
    ${row('r1 候选视频占比（实测）', pct(r.r1_candidate_video_ratio,3))}
    ${row('r2 二级→三级时长占比（实测）', pct(r.r2_stage2_to_stage3_ratio,3))}
    ${row('r1 × r2', fmt(r.r1_x_r2,6))}
    ${row('计算成本（货币/机位·小时）', fmt(m.compute,4))}
    ${row('出站流量成本', fmt(m.egress,4))}
    ${row('人工复核+反思摊销', fmt(m.feedback_human,4))}
    ${row('<b>合计（货币/机位·小时）</b>', '<b>'+fmt(m.total,4)+'</b>')}
    ${row('token 入/出（Stage3）', `${me.stage3_tokens_in||0} / ${me.stage3_tokens_out||0}`)}
    ${row('候选视频小时', fmt(me.candidate_video_hours,4))}
    ${row('第三级输入视频小时', fmt(me.stage3_input_hours,4))}`;

  const topos = D.topologies || [];
  $('topology-table').querySelector('tbody').innerHTML = topos.map(t => {
    const cm = (t.components_money_per_camera_hour||{});
    return `<tr><td><code>${esc(t.topology)}</code><div class="sub">${esc(t.topology_note||'')}</div></td>
      <td class="mono" style="text-align:right">${fmt((t.components_gpu_seconds_per_camera_hour||{}).total_gpu_seconds,2)}</td>
      <td class="mono" style="text-align:right">${fmt(cm.compute,4)}</td>
      <td class="mono" style="text-align:right">${fmt(cm.egress,4)}</td>
      <td class="mono" style="text-align:right">${fmt(cm.feedback_human,4)}</td>
      <td class="mono" style="text-align:right"><b>${fmt(cm.total,4)}</b></td></tr>`;
  }).join('');

  const sens = c.sensitivity || {};
  if ((sens.matrix||[]).length) {
    const head = (sens.matrix[0].r1_x_r2||[]).map((_, j) => {
      const r2lo = (sens.r2_range||[0,0])[0], r2hi = (sens.r2_range||[0,0])[1];
      const steps = (sens.matrix[0].r1_x_r2||[]).length;
      const r2 = r2lo + (r2hi-r2lo)*j/Math.max(1,steps-1);
      return `<th style="text-align:right">r2=${pct(r2,1)}</th>`;
    }).join('');
    const body = sens.matrix.map(r => `<tr><th>r1=${pct(r.r1,1)}</th>` +
      r.r1_x_r2.map(v => `<td class="mono" style="text-align:right">${v.toExponential(1)}</td>`).join('') + '</tr>').join('');
    $('sensitivity').innerHTML = `<table><thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody></table>
      <div class="sub">乘积范围 ${sens.product_min} ~ ${sens.product_max}；论文算术参考：5e-4 ~ 1e-2
      ${sens.matches_paper_range ? '<span class="pill ok">口径一致</span>' : '<span class="pill warn">范围不一致</span>'}</div>`;
  }
  $('cost-caveats').innerHTML = (c.caveats||[]).map(x => `<div class="note">${esc(x)}</div>`).join('');
}

function renderAudit() {
  const a = D.audit || {}, r = D.metrics || {}, ar = r.no_event_rejection || {};
  const rows = (a.windows||[]).slice(0,30).map(w => `<tr>
    <td>${esc(w.camera_id)}</td><td class="mono">${fmt(w.window_start,1)} → ${fmt(w.window_end,1)}</td>
    <td><span class="pill ${w.decision==='NO_EVENT'?'ok':(w.decision==='EVENT'?'bad':'warn')}">${esc(w.decision)}</span></td>
    <td class="mono">${fmt(w.score,3)}</td>
    <td>${w.event_in_window ? '<span class="pill bad">窗口内含真事件</span>' : '<span class="pill ok">无事件</span>'}</td>
  </tr>`).join('');
  $('audit-table').querySelector('tbody').innerHTML = rows || '<tr><td colspan="5" class="sub">无抽样</td></tr>';
  $('audit-summary').innerHTML = `
    <div class="kv">
      <div class="k">抽样窗口数</div><div class="mono">${a.samples||0}</div>
      <div class="k">抽样强度</div><div class="mono">${fmt(a.sampling,2)} 窗口 / 机位·小时</div>
      <div class="k">静默抑制率</div><div class="mono">${pct(ar.rejection_rate)} (CI95 ${esc(JSON.stringify(ar.ci95||[]))})</div>
      <div class="k">未决（转人工）</div><div class="mono">${ar.uncertain||0}</div>
      <div class="k">系统异常</div><div class="mono">${ar.system_error||0}</div>
    </div>
    <div class="note">Confirm/Dismiss 反馈只覆盖已显示的告警，存在选择偏差；本抽样用于估计被静默抑制的真实事件比例。</div>`;
}

function renderReliabilityTable() {
  const rel = D.reliability || {};
  $('rel-table').querySelector('tbody').innerHTML = (rel.per_event||[]).map(e => `<tr>
    <td class="mono">${esc(e.event_id)}</td><td>${esc(e.camera_id)}</td>
    <td class="mono">${e.stage1_candidates}</td><td class="mono">${e.stage2_event}</td>
    <td class="mono">${e.stage3_displayed}</td>
    <td>${e.lost_at === 'none' ? '<span class="pill ok">完整保留</span>' :
        `<span class="pill bad">丢失于 ${esc(e.lost_at)}</span>`}</td></tr>`).join('');
}

function renderRules() {
  const r = D.rules || {};
  $('rules-meta').innerHTML = `
    <div class="kv">
      <div class="k">规则集</div><div class="mono">${esc(r.ruleset_id||'')} @ ${esc(r.version_label||'')}</div>
      <div class="k">内容哈希</div><div class="mono">${esc(r.digest||'')}</div>
      <div class="k">规则条数</div><div class="mono">${esc((r.rules||[]).length)}</div>
      <div class="k">默认动作</div><div class="mono">${esc((r.policy||{}).default_action||'')}</div>
    </div>`;
  $('ledger-table').querySelector('tbody').innerHTML = (D.ledger||[]).slice().reverse().map(x => `<tr>
    <td class="mono">${esc(x.ts||'')}</td><td>${esc(x.action||'')}</td>
    <td class="mono">${esc(x.ruleset_hash||'')}</td><td>${esc(x.version_label||'')}</td>
    <td>${esc(x.operator||'')}</td><td class="sub">${esc(x.reason||'')}</td>
    <td class="mono">${x.duration_ms === undefined ? '-' : fmt(x.duration_ms,2)+'ms'}</td></tr>`).join('');
}

function renderHistogram() {
  const h = D.histogram || {};
  const counts = h.counts || [], pos = h.positives || [];
  if (!counts.length) { $('histogram').innerHTML = '<div class="sub">无帧分数</div>'; return; }
  const max = Math.max(...counts, 1);
  const W = 520, H = 150, bw = W / counts.length;
  let bars = '';
  counts.forEach((c, i) => {
    const hp = (pos[i]||0) / max * H, ht = c / max * H;
    bars += `<rect x="${(i*bw).toFixed(1)}" y="${(H-ht).toFixed(1)}" width="${(bw-3).toFixed(1)}"
      height="${ht.toFixed(1)}" fill="#2f3c4d"></rect>
      <rect x="${(i*bw).toFixed(1)}" y="${(H-hp).toFixed(1)}" width="${(bw-3).toFixed(1)}"
      height="${hp.toFixed(1)}" fill="#4aa8ff" opacity="0.85"></rect>`;
  });
  $('histogram').innerHTML = `<svg viewBox="0 0 ${W} ${H+24}" width="100%" height="190">${bars}
    <line x1="0" y1="${H}" x2="${W}" y2="${H}" stroke="#2a3441"/>
    ${counts.map((_,i)=>`<text x="${(i*bw+bw/2).toFixed(1)}" y="${H+16}" fill="#8b98a5"
      font-size="10" text-anchor="middle">${(i/10).toFixed(1)}</text>`).join('')}</svg>
    <div class="legend"><span><i class="dot" style="background:#2f3c4d"></i>全部帧</span>
    <span><i class="dot" style="background:#4aa8ff"></i>真事件帧</span>
    <span>横轴：帧级异常分（仅统计防区内目标）</span></div>`;
}

function renderNotes() {
  const r = D.metrics || {}, tc = r.triage_counts || {}, notes = [];
  if (r.sample_size_warning) notes.push(['warn', r.sample_size_warning]);
  if ((tc.SYSTEM_ERROR||0) > 0) notes.push(['bad',
    `出现 ${tc.SYSTEM_ERROR} 个采集中断窗口（丢帧/解码异常）。这些窗口已进入重检队列，未判定为"正常"。`]);
  if ((r.deferred_alarms||0) > 0) notes.push(['warn',
    `${r.deferred_alarms} 张卡片因证据不足或存疑转人工复核，计入复核成本但不计入确证召回。`]);
  if ((r.false_alarms||0) > 0) notes.push(['warn',
    `存在 ${r.false_alarms} 次合并误报；报告保留原始告警以供归因（静态物体/反光/授权误判等）。`]);
  const rel = D.reliability || {};
  if (rel.bottleneck) notes.push(['info', `当前瓶颈在 ${rel.bottleneck}；单独提升后级推理能力无法补回入口丢失的事件。`]);
  const loc = r.localization || {};
  if ((loc.n||0) > 0) notes.push(['info',
    `定位精度只统计已命中且真值提供 evidence_span 的 ${loc.n} 个事件；因果模式下终点被触发时刻截断，`
    + `终点误差应结合"终点截断"与"扣除截断后 MAE"一起读。`]);
  notes.push(['info', '时延两种口径：阈值满足→告警（系统处理时延）、事件起点→告警（用户实际等待，含规程等待）。']);
  notes.push(['info', '指标口径：事件召回按 t_trigger 落点一对一匹配；FA/CH 分母为逐路有效观测小时之和；'
    + 'TTA 起点见上条，终点为卡片完整显示时刻。']);
  $('notes').innerHTML = notes.map(([cls, text]) =>
    `<div class="note ${cls==='bad'?'bad-note':(cls==='warn'?'warn-note':'')}">${esc(text)}</div>`).join('');
}

function renderLocalization() {
  const r = D.metrics || {}, loc = r.localization || {};
  const rows = loc.per_event || [];
  $('loc-summary').innerHTML = `
    <div class="kv2">
      <div><div class="lab">样本数 n</div><div class="val">${loc.n||0}</div></div>
      <div><div class="lab">窗口内起点 MAE</div><div class="val">${fmt(loc.ref_start_mae_s,2)}s</div></div>
      <div><div class="lab">窗口内终点 MAE</div><div class="val">${fmt(loc.ref_end_mae_s,2)}s</div></div>
      <div><div class="lab">窗口内 mIoU</div><div class="val">${fmt(loc.ref_miou_mean,3)}</div></div>
      <div><div class="lab">窗口内边界命中率</div><div class="val">${pct(loc.ref_boundary_hit_rate)}</div></div>
      <div><div class="lab">证据覆盖率 / 精确率</div><div class="val">${pct(loc.ref_coverage_mean)} / ${pct(loc.ref_precision_mean)}</div></div>
      <div><div class="lab">原始起点 MAE</div><div class="val">${fmt(loc.start_mae_s,1)}s</div></div>
      <div><div class="lab">原始终点 MAE</div><div class="val">${fmt(loc.end_mae_s,1)}s</div></div>
      <div><div class="lab">终点结构性截断 p50</div><div class="val">${fmt(loc.end_truncation_p50_s,1)}s</div></div>
      <div><div class="lab">因果窗口上限</div><div class="val">${fmt(loc.window_limit_s,0)}s</div></div>
    </div>
    <div class="note">${esc(loc.note||'')} 未纳入统计的已命中事件：${loc.skipped_matched_without_span||0} 个（真值缺 evidence_span）。</div>`;
  $('loc-table').querySelector('tbody').innerHTML = rows.map(x => `<tr>
    <td class="mono">${esc(x.event_id)}</td><td class="mono">${esc(x.alarm_id)}</td>
    <td class="mono">${esc(JSON.stringify(x.evidence_span))}</td>
    <td class="mono">${esc(JSON.stringify(x.causal_reference))}</td>
    <td class="mono">${esc(JSON.stringify(x.alarm_interval))}</td>
    <td class="mono">${fmt(x.ref_start_error_s,2)}</td>
    <td class="mono">${fmt(x.ref_end_error_s,2)}</td>
    <td class="mono">${fmt(x.end_truncation_s,1)}</td>
    <td class="mono">${fmt(x.start_error_s,1)} / ${fmt(x.end_error_s,1)}</td>
    <td class="mono">${fmt(x.ref_iou,3)}</td>
    <td>${x.within_tolerance_ref ? '<span class="pill ok">是</span>' : '<span class="pill warn">否</span>'}</td>
  </tr>`).join('') || '<tr><td colspan="11" class="sub">没有可统计的定位样本</td></tr>';
}

function renderDifficult() {
  const d = (D.metrics||{}).difficult_cases || {};
  const c = d.counts || {};
  $('diff-summary').innerHTML = `
    <div class="kv2">
      <div><div class="lab">短暂停留（未触发）</div><div class="val ok">${c.short_stay||0}</div></div>
      <div><div class="lab">证据不完整（跟踪丢失）</div><div class="val warn">${c.evidence_incomplete||0}</div></div>
      <div><div class="lab">授权作业抑制</div><div class="val">${c.authorized_suppressed||0}</div></div>
      <div><div class="lab">证据不足转人工</div><div class="val warn">${c.insufficient_evidence||0}</div></div>
      <div><div class="lab">采集中断</div><div class="val bad">${c.system_error||0}</div></div>
      <div><div class="lab">静默的无事件窗口</div><div class="val ok">${c.no_event_windows||0}</div></div>
    </div>
    <div class="note">${esc(d.note||'')}</div>`;
  const table = (title, items, cols) => {
    if (!items || !items.length) return '';
    return `<h3>${esc(title)}</h3><table><thead><tr>${cols.map(x=>`<th>${esc(x[0])}</th>`).join('')}</tr></thead>
      <tbody>${items.slice(0,8).map(it => `<tr>${cols.map(x=>`<td class="${x[2]||''}">${esc(x[1](it))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  };
  $('diff-table').innerHTML =
    table('短暂停留（正常视频，不打扰）', d.short_stay, [
      ['机位', x => x.camera_id, 'mono'], ['防区', x => x.roi_id, 'mono'],
      ['进入', x => fmt(x.t_enter,1)+'s', 'mono'], ['离开', x => fmt(x.t_exit,1)+'s', 'mono'],
      ['累计/阈值', x => fmt(x.accum_s,1)+'/'+fmt(x.threshold_s,0)+'s', 'mono'],
      ['说明', x => x.reason + (x.occlusion_gap ? '（含遮挡）' : ''), 'sub']]) +
    table('证据不完整（不冒充连续停留）', d.evidence_incomplete, [
      ['机位', x => x.camera_id, 'mono'], ['防区', x => x.roi_id, 'mono'],
      ['进入', x => fmt(x.t_enter,1)+'s', 'mono'], ['结束', x => fmt(x.t_end,1)+'s', 'mono'],
      ['已确认累计', x => fmt(x.accum_s,1)+'s', 'mono'], ['原因', x => x.reason, 'sub']]) +
    table('授权作业（视觉事实成立、规程判定不违规）', d.authorized_suppressed, [
      ['告警', x => x.alarm_id, 'mono'], ['机位', x => x.camera_id, 'mono'],
      ['类别', x => x.event_class, 'mono'], ['依据', x => x.reason, 'sub']]) +
    table('证据不足转人工', d.insufficient_evidence, [
      ['告警', x => x.alarm_id, 'mono'], ['机位', x => x.camera_id, 'mono'],
      ['类别', x => x.event_class, 'mono'], ['原因', x => x.reason, 'sub']]) +
    table('采集中断（不判正常）', d.system_error, [
      ['告警', x => x.alarm_id, 'mono'], ['机位', x => x.camera_id, 'mono'],
      ['原因', x => x.reason, 'sub']]);
}

function renderResources() {
  const m = D.meta || {}, res = m.resources || {}, models = m.models || {},
        proto = m.protocol || {}, cap = m.capabilities || {};
  const gpu = res.gpu || {}, calls = res.actual_calls || {};
  $('res-summary').innerHTML = `
    <div class="kv2">
      <div><div class="lab">完整处理耗时</div><div class="val">${fmt(res.wall_seconds,2)}s</div></div>
      <div><div class="lab">吞吐</div><div class="val">${fmt(res.throughput_fps,0)} 帧/s</div></div>
      <div><div class="lab">峰值内存</div><div class="val">${res.peak_memory_mb===null||res.peak_memory_mb===undefined?'-':fmt(res.peak_memory_mb,1)+' MB'}</div></div>
      <div><div class="lab">峰值显存</div><div class="val">${gpu.measured_peak_vram_gb===null||gpu.measured_peak_vram_gb===undefined?'未测（CPU 参考实现）':fmt(gpu.measured_peak_vram_gb,1)+' GB'}</div></div>
      <div><div class="lab">Stage2 调用</div><div class="val">${calls.stage2_localizer||0}</div></div>
      <div><div class="lab">Stage3 调用</div><div class="val">${calls.stage3_verifier||0}</div></div>
      <div><div class="lab">Token 入/出</div><div class="val">${(res.tokens||{}).input||0} / ${(res.tokens||{}).output||0}</div></div>
      <div><div class="lab">人工复核估算</div><div class="val">${fmt(res.human_review_minutes,1)} 分钟</div></div>
    </div>
    <div class="note">${esc(res.note||'')} ${esc(gpu.note||'')}</div>`;
  const rows = ['detector','localizer','verifier','vlm'].map(k => {
    const it = models[k] || {};
    return `<tr><td class="mono">${esc(k)}</td><td>${esc(it.id||'-')}</td>
      <td class="mono">${esc(it.version||'-')}</td><td>${esc(it.provider||'-')}</td>
      <td>${esc(it.quantization||'-')}</td><td class="sub">${esc(it.note||it.endpoint||'')}</td></tr>`;
  }).join('');
  $('models-table').querySelector('tbody').innerHTML = rows;
  const capRows = Object.entries(cap).map(([k, v]) => {
    const st = (v||{}).status || '';
    const cls = st.indexOf('deferred') >= 0 ? 'warn' : (st.indexOf('implemented') === 0 ? 'ok' : 'info');
    return `<tr><td class="mono">${esc(k)}</td><td><span class="pill ${cls}">${esc(st)}</span></td>
      <td class="sub">${esc((v||{}).note||'')}</td></tr>`;
  }).join('');
  $('cap-table').querySelector('tbody').innerHTML = capRows;
  $('proto-line').innerHTML = `评测协议：<code>${esc(proto.mode||'none')}</code>` +
    (proto.mode === 'holdout'
      ? ` · 开发段 ${esc(JSON.stringify(proto.dev||{}))} · 测试段 ${esc(JSON.stringify(proto.test||{}))}
         · 跳过的审计窗口 ${proto.audit_windows_skipped||0}`
      : ` · 全量评测（未启用开发/测试隔离）`);
}

function boot() {
  D = window.__DATA__ || {};
  if (!D.meta && !D.metrics) { return; }
  renderHeader(); renderKpis(); renderTriage(); renderEvents(); renderAlarms();
  renderCost(); renderAudit(); renderReliabilityTable(); renderRules();
  renderLocalization(); renderDifficult(); renderResources();
  renderHistogram(); renderNotes();
  const s = $('alarm-search');
  if (s) s.addEventListener('input', renderAlarms);
  $('generated').textContent = D.generated_at || '';
}
document.addEventListener('DOMContentLoaded', boot);
"""


def render_page(payload: dict, title: str = "持续视频监控异常告警 · 工程评测报告",
                live: bool = False) -> str:
    """生成页面。live=True 时页面会轮询 /api/run 刷新数据。"""
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    data_decl = "window.__DATA__ = " + ("null" if live else data_json) + ";"
    live_js = """
async function poll(){
  if (window.__REVIEW_BUSY__ || (document.activeElement && document.activeElement.closest('.review-form'))) return;
  try {
    const resp = await fetch('/api/run', {cache:'no-store'});
    if (resp.ok) { window.__DATA__ = await resp.json(); boot(); }
  } catch (e) {}
}
if (window.__LIVE__) { poll(); setInterval(poll, 4000); }
""" if live else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title>
<style>{CSS}</style></head>
<body>
<header>
  <h1>持续视频监控 · VLM 异常告警工程评测</h1>
  <div class="sub" id="hdr-sub"></div>
  <div class="badge-line" id="hdr-badge"></div>
</header>
<main>
  <section><div class="grid kpis" id="kpis"></div></section>

  <section>
    <h2>分级漏斗与条件召回</h2>
    <div class="split">
      <div class="card"><div class="funnel" id="funnel"></div></div>
      <div class="card"><h3 style="margin-top:0">串联系统的条件概率</h3><div id="funnel-prob"></div></div>
    </div>
  </section>

  <section>
    <h2>事件级评测</h2>
    <div class="card">
      <table id="events-table"><thead><tr>
        <th>事件</th><th>摄像头</th><th>类别</th><th>违规区间(s)</th><th>条件成立(s)</th>
        <th>匹配结果</th><th>TTA</th><th>IoU</th><th>备注</th>
      </tr></thead><tbody></tbody></table>
    </div>
    <div class="split" style="margin-top:14px">
      <div class="card"><h3 style="margin-top:0">逐事件保留情况</h3>
        <table id="rel-table"><thead><tr><th>事件</th><th>机位</th><th>候选</th>
        <th>定位</th><th>显示</th><th>丢失环节</th></tr></thead><tbody></tbody></table></div>
      <div class="card"><h3 style="margin-top:0">帧级异常分分布</h3><div id="histogram"></div></div>
    </div>
  </section>

  <section>
    <h2>证据定位精度（与事件存在性分开统计）</h2>
    <div class="card"><div id="loc-summary"></div>
      <table id="loc-table"><thead><tr>
        <th>事件</th><th>告警</th><th>真值证据区间</th><th>可观测参考区间</th><th>告警证据区间</th>
        <th>参考起点误差</th><th>参考终点误差</th><th>终点截断</th><th>原始误差(起/终)</th>
        <th>参考 IoU</th><th>窗口内命中</th>
      </tr></thead><tbody></tbody></table>
    </div>
  </section>

  <section>
    <h2>告警卡片（结构化证据 + 回放）</h2>
    <div class="toolbar"><input type="search" id="alarm-search" placeholder="搜索告警 / 摄像头 / 事实…">
      <span class="sub">卡片字段固定：Event_Class · Temporal_Anchor · Physical_Fact_Evidence · Normative_Inference_Uncertainty</span></div>
    <div id="alarm-list"></div>
  </section>

  <section>
    <h2>正常与困难输入（全运行范围）</h2>
    <div class="card"><div id="diff-summary"></div><div id="diff-table"></div></div>
  </section>

  <section>
    <h2>全链路成本估算</h2>
    <div class="split">
      <div class="card"><h3 style="margin-top:0">C_total = C_always_on + r1·C2 + r1·r2·C3 + C_feedback</h3>
        <table id="cost-table"></table></div>
      <div class="card"><h3 style="margin-top:0">r1 × r2 灵敏度（乘积即第三级输入比例）</h3>
        <div id="sensitivity"></div></div>
    </div>
    <div class="card" style="margin-top:14px"><h3 style="margin-top:0">三种部署拓扑对比（同一实测计量）</h3>
      <table id="topology-table"><thead><tr><th>拓扑</th><th style="text-align:right">GPU·s/机位·h</th>
      <th style="text-align:right">计算</th><th style="text-align:right">出站</th>
      <th style="text-align:right">人工</th><th style="text-align:right">合计/机位·h</th></tr></thead><tbody></tbody></table>
      <div id="cost-caveats"></div>
    </div>
  </section>

  <section>
    <h2>可用资源与模型版本</h2>
    <div class="card"><div id="res-summary"></div>
      <h3>模型清单</h3>
      <table id="models-table"><thead><tr><th>环节</th><th>模型/实现</th><th>版本</th>
        <th>来源</th><th>量化</th><th>备注</th></tr></thead><tbody></tbody></table>
      <h3>能力状态（首版范围 vs 暂缓项）</h3>
      <table id="cap-table"><thead><tr><th>能力</th><th>状态</th><th>说明</th></tr></thead>
        <tbody></tbody></table>
      <div class="sub" id="proto-line"></div>
    </div>
  </section>

  <section>
    <h2>抽样审计与无事件拒识</h2>
    <div class="split">
      <div class="card"><h3 style="margin-top:0">审计汇总</h3><div id="audit-summary"></div></div>
      <div class="card"><h3 style="margin-top:0">最近抽样窗口</h3>
        <table id="audit-table"><thead><tr><th>机位</th><th>窗口</th><th>判定</th>
        <th>证据分</th><th>真值</th></tr></thead><tbody></tbody></table></div>
    </div>
  </section>

  <section>
    <h2>规则版本与审计账本</h2>
    <div class="split">
      <div class="card"><h3 style="margin-top:0">当前生效规则集</h3><div id="rules-meta"></div>
        <div class="note">规则变更必须经：隔离待审 → 静态校验 → 回归门禁 → 原子发布/回滚。</div></div>
      <div class="card"><h3 style="margin-top:0">变更账本（含回滚耗时）</h3>
        <table id="ledger-table"><thead><tr><th>时间</th><th>动作</th><th>哈希</th>
        <th>版本</th><th>操作者</th><th>原因</th><th>耗时</th></tr></thead><tbody></tbody></table></div>
    </div>
  </section>

  <section><h2>失效模式归因与实证建议</h2><div id="notes"></div></section>
</main>
<footer>
  生成时间 <span id="generated" class="mono"></span> · cvalarm 工程实现 · 本页无外部依赖，可离线打开
</footer>
<script>{data_decl}</script>
<script>window.__LIVE__ = {str(live).lower()};</script>
<script>{JS}</script>
<script>{live_js}</script>
</body></html>"""
