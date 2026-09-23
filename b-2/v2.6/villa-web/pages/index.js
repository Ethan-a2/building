import { useEffect, useRef, useState } from 'react';
import Head from 'next/head';
import { createScene } from '../lib/scene';
import { runChecks, parseStair } from '../lib/checks';
import { SPACES, PATHS } from '../lib/specs';

const CATS = ['楼梯', '通行', '净空', '房间', '家具', '采光', '场地', '改造'];
const VC = { pass: '#2e9e5b', warn: '#d69120', fail: '#d64545' };
const VT = { pass: '通过', warn: '注意', fail: '不满足' };

export default function Home() {
  const boxRef = useRef(null);
  const apiRef = useRef(null);
  const qs = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : new URLSearchParams();
  const num = (k, d) => (qs.has(k) ? Number(qs.get(k)) : d);
  const bool = (k, d) => (qs.has(k) ? qs.get(k) !== '0' : d);
  const [model, setModel] = useState(null);
  const [checks, setChecks] = useState([]);
  const [ui, setUi] = useState({
    explode: num('explode', 35) / 100,
    section: qs.get('section') ? 1.2 : null,
    f1: bool('f1', true), f2: bool('f2', true), roof: bool('roof', true),
    labels: bool('labels', true), furn: bool('furn', false),
  });
  const [walk, setWalk] = useState({ id: qs.get('path') || 'p1', playing: false, cur: null, prog: 0 });
  const [measure, setMeasure] = useState({ on: false, pts: [], dist: null });
  const [picked, setPicked] = useState(null);
  const [tab, setTab] = useState(qs.get('tab') === 'walk' ? 'walk' : 'checks');

  // ---- 载入模型 + 静态校验 ----
  useEffect(() => {
    fetch('/model.json').then((r) => r.json()).then((d) => {
      setModel(d);
      setChecks(runChecks(d));
    });
  }, []);

  // ---- 初始化 three.js ----
  useEffect(() => {
    if (!model || !boxRef.current || apiRef.current) return;
    const api = createScene(boxRef.current, model);
    apiRef.current = api;

    // 3D 射线净空实测（必须在整体未爆炸状态下实测，避免层偏移干扰）
    const st = parseStair(model);
    const hr = [];
    st.steps.forEach((s, i) => {
      hr.push({
        name: `楼梯第 ${i + 1} 级踏面净空`,
        value: api.headroomAt((s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2, s.z1),
        note: '行走线中点自踏面竖向实测首个障碍',
      });
    });
    hr.push({ name: '入户口上方(第二跑尾段下)净空', value: api.headroomAt(6.05, 1.2, 0), note: '第二跑压在入口上方，实测尾段踏步底面' });
    hr.push({ name: '入口门内 0.5m 净空', value: api.headroomAt(6.05, 0.6, 0), note: '入户正上方为二层楼板' });
    hr.push({ name: '楼梯间东侧走道净空', value: api.headroomAt(7.14, 2.5, 0), note: '0.8m 走道中段至屋面板' });
    hr.push({ name: '北端户门前净空', value: api.headroomAt(6.3, 4.5, 0), note: '两户入户门之间缓冲段' });
    hr.push({ name: '二层楼梯洞口处净空', value: api.headroomAt(6.3, 2.0, 3.0), note: '二层楼面至屋面板（洞口上方无梁）' });
    setChecks(runChecks(model, hr));

    // 实测完成后再套用初始视图状态
    api.setExplode(ui.explode);
    api.setVis({ f1: ui.f1, f2: ui.f2, roof: ui.roof, labels: ui.labels, furn: ui.furn });
    if (ui.section != null) api.setSection(ui.section);
  }, [model]);

  // ---- 控件 ----
  const api = () => apiRef.current;
  const setUI = (patch) => {
    setUi((u) => {
      const n = { ...u, ...patch };
      const a = api();
      if (a) {
        a.setExplode(n.explode);
        a.setVis({ f1: n.f1, f2: n.f2, roof: n.roof, labels: n.labels, furn: n.furn });
        a.setSection(n.section);
      }
      return n;
    });
  };

  // ---- 点击：测距 / 选中对象 ----
  const onClick = (e) => {
    const a = api(); if (!a) return;
    if (measure.on) {
      const p = a.probeGround(e.clientX, e.clientY);
      if (!p) return;
      setMeasure((m) => {
        const pts = [...m.pts, p];
        if (pts.length === 2) {
          const d = pts[0].distanceTo(pts[1]);
          return { on: true, pts: [], dist: +d.toFixed(2) };
        }
        return { ...m, pts };
      });
      return;
    }
    const hit = a.pick(e.clientX, e.clientY);
    if (hit) {
      const sp = SPACES.find((s) => s.rects.some((r) => hit.point.x >= r[0] && hit.point.x <= r[2] && hit.point.y >= r[1] && hit.point.y <= r[3]));
      setPicked({ name: hit.name, point: hit.point.toArray().map((v) => +v.toFixed(2)), space: sp || null });
    }
  };

  // ---- 通行模拟 ----
  const play = () => {
    const a = api(); if (!a) return;
    setUI({ f1: true, f2: true });
    setWalk((w) => ({ ...w, playing: true, prog: 0, cur: null }));
    a.playWalk(walk.id, (s, prog) => setWalk((w) => ({ ...w, cur: s, prog })));
  };

  // ESC 退出测距
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') setMeasure({ on: false, pts: [], dist: null }); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  // ---- 汇总 ----
  const summary = ['pass', 'warn', 'fail'].map((v) => checks.filter((c) => c.verdict === v).length);

  return (
    <>
      <Head><title>自建别墅 b-2 · 3D 交互预览与空间可行性校验</title></Head>
      <div className="page">
        <header>
          <h1>自建别墅 b-2 · 3D 交互预览</h1>
          <div className="sub">两层对称双户 · 12.6×13.0m · 南院 5m + 北退让 1m · 楼梯间南中入，进户左转上楼</div>
          <div className="badges">
            <span className="badge pass">{summary[0]} 项通过</span>
            <span className="badge warn">{summary[1]} 项注意</span>
            <span className="badge fail">{summary[2]} 项不满足</span>
          </div>
        </header>

        <div className="main">
          {/* 左：控制 */}
          <aside className="panel left">
            <h3>视图</h3>
            <div className="row btns">
              {[['god', '上帝视角'], ['home', '全楼'], ['f1', '一层'], ['plan', '平面'], ['stair', '楼梯间']].map(([k, n]) => (
                <button key={k} onClick={() => api()?.setPreset(k)}>{n}</button>
              ))}
            </div>
            <h3>错层展示</h3>
            <label>爆炸展开 <b>{Math.round(ui.explode * 100)}%</b>
              <input type="range" min="0" max="100" value={ui.explode * 100} onChange={(e) => setUI({ explode: +e.target.value / 100 })} />
            </label>
            <label className="row seg">
              剖切(Y=1.2 楼梯段)
              <input type="checkbox" checked={ui.section != null} onChange={(e) => setUI({ section: e.target.checked ? 1.2 : null })} />
            </label>
            <h3>图层</h3>
            {[['f1', '一层 + 场地'], ['f2', '二层'], ['roof', '屋面/女儿墙'], ['labels', '文字标注'], ['furn', '家具占位']].map(([k, n]) => (
              <label className="row seg" key={k}>
                {n}
                <input type="checkbox" checked={ui[k]} onChange={(e) => setUI({ [k]: e.target.checked })} />
              </label>
            ))}
            <h3>测量</h3>
            <button className={measure.on ? 'active' : ''} onClick={() => setMeasure({ on: !measure.on, pts: [], dist: null })}>
              {measure.on ? '测距中：点击地面两点 (ESC 关)' : '两点测距'}
            </button>
            {measure.dist != null && <div className="note">距离 = <b>{measure.dist} m</b></div>}
            {picked && (
              <div className="note">
                选中：{picked.name}<br />命中点 {picked.point.join(', ')}
                {picked.space && (
                  <div style={{ marginTop: 6 }}>
                    <b>{picked.space.name}</b> · {picked.space.en}
                    {checks.filter((c) => c.name.startsWith(picked.space.name)).map((c, i) => (
                      <div key={i} style={{ marginTop: 2 }}>
                        <span style={{ color: VC[c.verdict] }}>[{VT[c.verdict]}]</span>{' '}
                        {c.name.replace(picked.space.name + ' ', '')}：{c.value}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </aside>

          {/* 中：3D */}
          <div className="canvas" ref={boxRef} onClick={onClick} />

          {/* 右：校验 */}
          <aside className="panel right">
            <div className="tabs">
              <button className={tab === 'checks' ? 'on' : ''} onClick={() => setTab('checks')}>可行性校验</button>
              <button className={tab === 'walk' ? 'on' : ''} onClick={() => setTab('walk')}>通行模拟</button>
            </div>
            {tab === 'checks' && (
              <div className="scroll">
                {!checks.length && <div className="note">加载模型中…</div>}
                {CATS.map((cat) => {
                  const items = checks.filter((c) => c.cat === cat);
                  if (!items.length) return null;
                  return (
                    <div key={cat}>
                      <h3>{cat}</h3>
                      {items.map((c, i) => (
                        <div key={i} className={`item ${c.verdict}`}>
                          <div className="it-h">
                            <span className="nm">{c.name}</span>
                            <span className="vd" style={{ background: VC[c.verdict] }}>{VT[c.verdict]}</span>
                          </div>
                          <div className="it-v">实测 <b>{c.value}</b> · 标准 {c.limit}</div>
                          <div className="it-n">{c.note}</div>
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            )}
            {tab === 'walk' && (
              <div className="scroll">
                <h3>人体净空模拟</h3>
                <div className="note">按 1.75m 人体肩宽 0.44m 沿真实动线行进，实时射线实测头顶净空与侧向净距。</div>
                {PATHS.map((p) => (
                  <div key={p.id} className={`item ${walk.id === p.id ? 'sel' : ''}`} onClick={() => setWalk((w) => ({ ...w, id: p.id }))}>
                    <div className="it-h"><span className="nm">{p.name}</span></div>
                    <div className="it-n">{p.desc}</div>
                  </div>
                ))}
                <div className="row btns">
                  <button className="active" onClick={play}>▶ 播放</button>
                  <button onClick={() => { api()?.stopWalk(); setWalk((w) => ({ ...w, playing: false, cur: null })); }}>■ 停止</button>
                </div>
                {walk.cur && (
                  <div className="note live">
                    进度 {(walk.prog * 100).toFixed(0)}%
                    <div>位置 ({walk.cur.x.toFixed(2)}, {walk.cur.y.toFixed(2)}, +{walk.cur.z.toFixed(2)})</div>
                    <div>头顶净空 <b style={{ color: walk.cur.headroom >= 2 ? VC.pass : VC.fail }}>{walk.cur.headroom >= 9 ? '>9' : walk.cur.headroom} m</b></div>
                    <div>侧向净距 <b style={{ color: walk.cur.side >= 0.3 ? VC.pass : VC.fail }}>{walk.cur.side >= 9 ? '>8' : walk.cur.side} m</b></div>
                    {(walk.cur.headroom < 2 || walk.cur.side < 0.3) ? <div className="warn-t">⚠ 该点净空/净距不足</div> : <div className="ok-t">✓ 通行顺畅</div>}
                  </div>
                )}
                <h3>关键净空（射线实测）</h3>
                {checks.filter((c) => c.cat === '净空').map((c, i) => (
                  <div key={i} className={`item ${c.verdict}`}>
                    <div className="it-h"><span className="nm">{c.name}</span><span className="vd" style={{ background: VC[c.verdict] }}>{VT[c.verdict]}</span></div>
                    <div className="it-v">实测 <b>{c.value}</b> · 标准 {c.limit}</div>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>

        <footer>
          数据来源：Blender 实测模型（531 个体块）· 校核参照 GB 50096 住宅设计规范 / GB 50016 建筑设计防火规范 / 人体工学经验值 ·
          鼠标左键旋转 · 右键平移 · 滚轮缩放
        </footer>
      </div>
    </>
  );
}
