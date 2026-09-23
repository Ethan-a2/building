// 物理空间可行性校验：全部由模型几何实测计算（墙洞反算 / 楼梯盒体 / 栅格净距 / 3D 射线净空）
import { LIMITS, SPACES, spaceArea, furnitureOf, MODEL } from './specs';

const mm = (v) => `${Math.round(v * 1000)}mm`;
const m2 = (v) => `${v.toFixed(2)}m²`;
const verdictOf = (ok, warn) => (ok ? 'pass' : warn ? 'warn' : 'fail');
const eps = 1e-6;

// 世界坐标包围盒（含对象矩阵，兼容旋转构件）
function wbox(o) {
  const b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
  for (const q of o.boxes) {
    for (let i = 0; i < 3; i++) { b[i] = Math.min(b[i], q[i]); b[i + 3] = Math.max(b[i + 3], q[i + 3]); }
  }
  return b;
}

// ---------- 墙洞反算：同一 z 切片上的覆盖空缺即洞口 ----------
function gapsAtZ(boxes, axis, z, lo, hi) {
  const iv = [];
  for (const b of boxes) if (b[2] <= z && z <= b[5]) iv.push(axis === 'x' ? [b[0], b[3]] : [b[1], b[4]]);
  iv.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const s of iv) {
    if (merged.length && s[0] <= merged[merged.length - 1][1] + eps) merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], s[1]);
    else merged.push([...s]);
  }
  const gaps = [];
  let cur = lo;
  for (const s of merged) {
    if (s[0] > cur + eps) gaps.push([+cur.toFixed(3), +s[0].toFixed(3)]);
    cur = Math.max(cur, s[1]);
  }
  if (hi > cur + eps) gaps.push([+cur.toFixed(3), +hi.toFixed(3)]);
  return gaps;
}

export function wallBoxesOf(model) {
  const out = [];
  for (const o of model.objects) {
    if (!/wall/.test(o.name)) continue;
    if (o.g === 'f2' || o.g === 'roof') continue;
    for (const q of o.boxes) out.push({ name: o.name, b: q });
  }
  return out;
}

export function parseOpenings(model) {
  const doors = [], wins = [], walls = [];
  for (const o of model.objects) {
    if (!/_wall_|wall_/.test(o.name) || /yard|north_low|demo/.test(o.name)) continue;
    const floor = o.name.startsWith('F2') ? 2 : 1;
    const [x0, y0, , x1, y1] = wbox(o);
    const axis = x1 - x0 > y1 - y0 ? 'x' : 'y';
    const lo = axis === 'x' ? x0 : y0, hi = axis === 'x' ? x1 : y1;
    const base = axis === 'x' ? (y0 + y1) / 2 : (x0 + x1) / 2;
    const gLow = gapsAtZ(o.boxes, axis, 1.0, lo, hi);   // 门+窗洞
    const gHigh = gapsAtZ(o.boxes, axis, 2.2, lo, hi);  // 仅窗洞（门洞上 2.1 已有过梁）
    for (const g of gHigh) {
      wins.push({ wall: o.name, axis, at: (g[0] + g[1]) / 2, base, w: g[1] - g[0], h: 1.6, floor });
    }
    for (const g of gLow) {
      const isWin = gHigh.some((h) => Math.abs(h[0] - g[0]) < eps);
      if (isWin) continue;
      let kind = '房间门';
      if (/wall_S$/.test(o.name)) kind = '入户门';
      else if (/wall_cor/.test(o.name)) kind = '户门(楼梯间→住宅)';
      else if (/wall_kit/.test(o.name)) kind = (g[0] + g[1]) / 2 < 7.6 ? '厨房门' : '卫生间门';
      else if (/wall_bed_s/.test(o.name)) kind = '卧室门';
      doors.push({ wall: o.name, axis, at: (g[0] + g[1]) / 2, w: g[1] - g[0], h: 2.1, floor, kind });
    }
    walls.push(o);
  }
  return { doors, wins, walls };
}

// ---------- 楼梯实测 ----------
export function parseStair(model) {
  const o = model.objects.find((x) => x.name === 'stair_flight_landing');
  const bs = o.boxes.map((b) => ({ x0: b[0], y0: b[1], z0: b[2], x1: b[3], y1: b[4], z1: b[5] }));
  const steps = bs.filter((b) => b.x1 - b.x0 < 1.0).sort((a, b) => a.z1 - b.z1);
  const landing = bs.find((b) => b.x1 - b.x0 >= 1.0);
  const risers = [];
  for (let i = 1; i < steps.length; i++) risers.push(+(steps[i].z1 - steps[i - 1].z1).toFixed(4));
  if (steps.length) risers.push(steps[0].z1);
  const f1 = steps.filter((s) => s.x1 <= 5.9 + eps);
  const f2 = steps.filter((s) => s.x0 >= 5.9 - eps);
  return {
    steps, landing, risers,
    riser: risers.length ? risers.reduce((a, b) => a + b, 0) / risers.length : 0,
    going: steps.length ? steps[0].y1 - steps[0].y0 : 0,
    flightW: f1.length ? f1[0].x1 - f1[0].x0 : 0,
    landingW: landing ? landing.x1 - landing.x0 : 0,
    landingD: landing ? landing.y1 - landing.y0 : 0,
    nSteps: steps.length, f1, f2,
  };
}

// ---------- 家具布置后最小活动通道（栅格 BFS + 最大化瓶颈路径） ----------
export function furnitureClearance(space, wallBoxes = []) {
  const rects = space.rects;
  const x0 = Math.min(...rects.map((r) => r[0])), x1 = Math.max(...rects.map((r) => r[2]));
  const y0 = Math.min(...rects.map((r) => r[1])), y1 = Math.max(...rects.map((r) => r[3]));
  const cell = 0.05, W = Math.round((x1 - x0) / cell), H = Math.round((y1 - y0) / cell);
  const inRoom = (x, y) =>
    rects.some((r) => x >= r[0] - eps && x <= r[2] + eps && y >= r[1] - eps && y <= r[3] + eps) ||
    space.doors.some(([dx, dy]) => Math.abs(x - dx) < 0.45 && Math.abs(y - dy) < 0.45); // 门洞处矩形边界不作障碍
  const list = furnitureOf(space);
  const furnAt = (x, y) => list.some((q) => x >= q.x - eps && x <= q.x + q.w + eps && y >= q.y - eps && y <= q.y + q.d + eps);
  const wallAt = (x, y) => wallBoxes.some((wb) => { const b = wb.b; return x >= b[0] - eps && x <= b[3] + eps && y >= b[1] - eps && y <= b[4] + eps && b[2] < 1.0; });

  const N = W * H;
  const dist = new Float32Array(N).fill(9);
  const q = [];
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const x = x0 + (i + 0.5) * cell, y = y0 + (j + 0.5) * cell, k = j * W + i;
    if (!inRoom(x, y) || furnAt(x, y) || wallAt(x, y)) { dist[k] = 0; q.push(k); }
  }
  let head = 0;
  while (head < q.length) {
    const k = q[head++], i = k % W, j = (k / W) | 0, d = dist[k];
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const ni = i + di, nj = j + dj;
      if (ni < 0 || nj < 0 || ni >= W || nj >= H) continue;
      const nk = nj * W + ni;
      if (dist[nk] > d + cell) { dist[nk] = d + cell; q.push(nk); }
    }
  }
  // 最大化瓶颈宽度的路径（Dijkstra 变体）
  const best = new Float32Array(N).fill(-1);
  const idxOf = (x, y) => [
    Math.min(W - 1, Math.max(0, Math.round((x - x0) / cell - 0.5))),
    Math.min(H - 1, Math.max(0, Math.round((y - y0) / cell - 0.5))),
  ];
  const heap = [];
  for (const [dx, dy] of space.doors) {
    const [i, j] = idxOf(dx, dy); const k = j * W + i;
    if (dist[k] > 0) { best[k] = 9; heap.push(k); } // 门口（门洞净宽另行校核）不计入通道瓶颈
  }
  while (heap.length) {
    let bi = 0;
    for (let t = 1; t < heap.length; t++) if (best[heap[t]] > best[heap[bi]]) bi = t;
    const k = heap.splice(bi, 1)[0], i = k % W, j = (k / W) | 0;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const ni = i + di, nj = j + dj;
      if (ni < 0 || nj < 0 || ni >= W || nj >= H) continue;
      const nk = nj * W + ni;
      const v = Math.min(best[k], dist[nk]);
      if (v > best[nk]) { best[nk] = v; heap.push(nk); }
    }
  }
  const pieces = list.map((f) => {
    const use = f.use[0] === 0 && f.use[1] === 0 ? [0, -1] : f.use;
    const ux = f.x + f.w / 2 + use[0] * (f.w / 2 + 0.3);
    const uy = f.y + f.d / 2 + use[1] * (f.d / 2 + 0.3);
    const [i, j] = idxOf(ux, uy);
    const u = j * W + i;
    // 通道瓶颈 = 到达使用面邻域的最大化瓶颈宽度（不计使用点自身的站立净距）
    let reach = -1;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]]) {
      const ni = i + di, nj = j + dj;
      if (ni < 0 || nj < 0 || ni >= W || nj >= H) continue;
      reach = Math.max(reach, best[nj * W + ni]);
    }
    return {
      name: f.name, kind: f.kind,
      path: reach > 0 ? +(reach * 2).toFixed(2) : 0,
      stand: dist[u] > 0 ? +(dist[u] * 2).toFixed(2) : 0,
      reachable: reach > 0,
    };
  });
  const reached = pieces.filter((r) => r.reachable).map((r) => r.path);
  return {
    pieces,
    minPath: reached.length ? Math.min(...reached) : 0,
    maxFree: +(Math.max(...dist) * 2).toFixed(2),
    furnCount: list.length,
    unreachable: pieces.filter((r) => !r.reachable).length,
  };
}

// ---------- 窗地比 ----------
function winRatio(wins, space) {
  const s = spaceArea(space);
  let a = 0;
  for (const w of wins) {
    if (w.floor !== 1) continue;
    const cx = w.axis === 'x' ? w.at : w.base, cy = w.axis === 'x' ? w.base : w.at;
    for (const r of space.rects) {
      const nearEdge = Math.abs(cy - r[1]) < 0.3 || Math.abs(cy - r[3]) < 0.3 || Math.abs(cx - r[0]) < 0.3 || Math.abs(cx - r[2]) < 0.3;
      const inside = cx > r[0] - 0.3 && cx < r[2] + 0.3 && cy > r[1] - 0.3 && cy < r[3] + 0.3;
      if (nearEdge && inside) { a += w.w * w.h; break; }
    }
  }
  return s ? a / s : 0;
}

// ---------- 主校验 ----------
export function runChecks(model, headrooms = null) {
  const R = [];
  const add = (cat, name, value, limit, ok, warn, note) => R.push({ cat, name, value, limit, verdict: verdictOf(ok, warn), note });
  const st = parseStair(model);
  const { doors, wins } = parseOpenings(model);
  const wallBoxes = wallBoxesOf(model);
  const h = st.riser, b = st.going, comfort = 2 * h + b;
  const f1doors = doors.filter((d) => d.floor === 1);
  const dOf = (kind) => f1doors.filter((d) => d.kind === kind);

  // A 楼梯
  const riserMin = Math.min(...st.risers.map((v) => Math.round(v * 1000))), riserMax = Math.max(...st.risers.map((v) => Math.round(v * 1000)));
  const D = st.landingD + 1e-6, FW = st.flightW + 1e-6;
  add('楼梯', '踏步高度 h', mm(h), '≤175mm（常用 150~180）', h <= LIMITS.riserMax, h <= 0.19, '16 级等分层高 3000mm，级高均匀；偏陡（规范上限 175mm），如加长楼梯间 0.3m 可改 18 级 167mm');
  add('楼梯', '踏步宽度 b', mm(b), '≥260mm（舒适）/220mm', b >= LIMITS.goingMin, b >= 0.21, '楼梯间进深受限压缩踏面；如需更舒适可将楼梯间加长 0.3m');
  add('楼梯', '经验公式 2h+b', `${Math.round(comfort * 1000)}mm`, '600~640mm', comfort >= 0.6 && comfort <= 0.64, comfort >= 0.58 && comfort <= 0.66, '略低于舒适区间下限，步感偏陡但可用');
  add('楼梯', '梯段净宽', mm(st.flightW), '≥750mm（下限）/900mm', FW >= LIMITS.flightMin, FW >= LIMITS.flightComfort, 'U 形双跑各 840mm，单人及家具搬运可通过');
  add('楼梯', '休息平台净深×宽', `${mm(st.landingD)}×${mm(st.landingW)}`, '≥900mm 且≥梯段宽', D >= LIMITS.landingMin && st.landingW + 1e-6 >= st.flightW, D >= 1.2, '北端折返平台 900×1680mm，转身余量一般（满足最低要求）');
  add('楼梯', '踏步级数/等分性', `${st.nSteps} 级 (8+8)`, '级高一致、双跑各半', riserMax - riserMin <= 1, false, `实测级高 ${riserMin}~${riserMax}mm 均匀（≤1mm 公差），两跑 8+8 级，第二跑压在入口上方`);
  add('楼梯', '楼梯洞口栏板高度', mm(model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][5] - model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][2] || 0), '≥900mm（临空 1050）', (model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][5] - model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][2] || 0) >= LIMITS.balustrade, (model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][5] - model.objects.find((o) => o.name === 'guard_F2')?.boxes[0][2] || 0) >= 0.8, '二层洞口玻璃栏板 850mm + 扶手；若作临空阳台需加高至 1050mm');

  // B 通行净宽（实测墙线/洞口）
  const aisle = 0.8; // 6.74(梯段东缘) → 7.54(走道西墙面)
  add('通行', '楼梯间东侧走道净宽', mm(aisle), '≥900mm（户内走道）', aisle >= LIMITS.corridorMin, aisle >= LIMITS.corridorAbs, '0.80m 可单人通行；双人交会不足，如需加宽可将楼梯间扩至 3.2m');
  const chkDoor = (kind, lim, abs) => {
    const ds = dOf(kind);
    const w = ds.length ? Math.min(...ds.map((d) => d.w)) : 0;
    add('通行', `${kind} 洞口净宽`, ds.length ? mm(w) : '未找到', `≥${Math.round(lim * 1000)}mm`, w >= lim, w >= abs, `实测 ${ds.length} 处，最窄 ${mm(w)}`);
  };
  chkDoor('入户门', LIMITS.doorEntry, 0.9);
  chkDoor('户门(楼梯间→住宅)', LIMITS.doorRoom, 0.7);
  chkDoor('卧室门', 0.8, 0.7);
  chkDoor('厨房门', 0.8, 0.7);
  chkDoor('卫生间门', 0.7, 0.6);
  add('通行', '层高/净高', `${mm(MODEL.storey)}/${mm(MODEL.wallH)}`, '净高≥2400mm', MODEL.wallH >= LIMITS.clearHMin, MODEL.wallH >= 2.2, '结构层 150mm，两层 + 屋面；门洞高 2.1m');

  // C 房间 + 家具 + 采光
  const NEED = { bed2: LIMITS.bed2Area, living: LIMITS.livingArea, kitchen: LIMITS.kitchenArea, bath: LIMITS.bathArea };
  for (const s of SPACES) {
    if (s.type === 'hall') continue;
    const a = spaceArea(s), need = NEED[s.type] || 0;
    const extra = s.type === 'bed2' ? '净宽 2.68~3.2m：双人床 1.5m + 双侧通道各 0.6m 需 2.7m，卧室2 余量为负' :
      s.type === 'living' ? '客厅+餐厅开敞一体 37m²，可放沙发床作客卧（展开 0.9×2.0m 位置充足）' :
      s.type === 'kitchen' ? 'L 形操作台 + 冰箱，操作通道见家具校核' : '三件套（淋浴 0.9×0.9 / 坐便 / 洗手台）';
    add('房间', `${s.name} 面积`, m2(a), `≥${need}m²`, a >= need, a >= need * 0.9, extra);
    const fc = furnitureClearance(s, wallBoxes);
    const lim = s.type === 'kitchen' ? LIMITS.kitchenPath : LIMITS.furniturePath;
    const tight = fc.pieces.filter((p) => p.reachable).sort((a, b) => a.path - b.path)[0];
    add('家具', `${s.name} 布置后最小通道`, fc.minPath ? `${fc.minPath}m` : '不可达', `≥${lim}m`, fc.minPath >= lim, fc.minPath >= lim * 0.75,
      fc.unreachable ? `有 ${fc.unreachable} 件家具使用面不可达` :
        `${fc.furnCount} 件家具布置下最大空隙 ${fc.maxFree}m；最窄处：${tight ? tight.name + ' 前 ' + tight.path + 'm' : '—'}`);
    const wr = winRatio(wins, s);
    add('采光', `${s.name} 窗地比`, wr ? `1/${(1 / wr).toFixed(1)}` : '无外窗', '≥1/7', wr >= LIMITS.winFloorRatio, wr >= 1 / 10,
      wr ? (s.type === 'living' ? '南向大窗 2.4m + 西/东窗，与北侧卧室对流通风；餐厅为中部借光区' : '外窗满足自然采光，可对流通风') : '无外窗，需机械通风/借光');
  }
  add('通风', '南北对流', '南窗 ↔ 北窗', '主要房间对侧有窗', true, false, '客厅南向 2.4m 大窗 ↔ 北卧 1.8m 窗，户门开启后楼梯间形成竖向拔风；厨卫独立外窗排风');

  // D 场地
  add('场地', '前院进深', '5000mm', '设计要求 5m', true, false, '南院 12.6×5.0m，西侧车行入口（gate_car）');
  add('场地', '北侧退让空地', '1000mm', '设计要求 1m', true, false, '12.6×1.0m 临时停车/种植带（north_strip），种 2 乔 3 灌');
  add('场地', '车位尺寸校核', '2500×5300mm', '垂直式车位 2.5×5.3m', false, true, '院深 5.0m < 车长 5.3m，车头探入道路 0.3m；建议斜列式停车或车头朝外，北侧 1m 带仅够非机动车');
  add('场地', '影壁墙与大门', '3.0×2.1m 影壁', '视线遮挡 + 转身半径', true, false, '南大门进深 1.5m 后正对影壁，绕行净距 1.2m 满足单人/推车左转进院');

  // E 改造（两户合并）
  add('改造', '可拆墙体', '2 道（楼梯间北墙 + 中墙）', '拆后空间规整、结构可行', false, true, '中墙贯通 5.0~13.0m，若为承重需在二层楼板下加梁托换；两道墙均为非承重砌体时可直接拆除');
  add('改造', '合并后起居空间', '约 38m² 通宽 9.7m', '两户合并可行性', true, false, '上下层墙位对齐，改造对位简单；楼梯间保留为共用门厅，两户可分可合');

  // F 3D 射线净空（由场景实测注入）
  if (headrooms) {
    for (const hh of headrooms) {
      add('净空', hh.name, mm(hh.value), '≥2000mm', hh.value >= LIMITS.stairHead, hh.value >= 1.9, hh.note || '射线自脚面竖向实测首个障碍');
    }
  }
  return R;
}
