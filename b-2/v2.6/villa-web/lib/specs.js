// 空间与家具规格（单位：米；坐标与 Blender 模型一致：X 向东 0→12.6，Y 向北 0→13，Z 向上）
// 布局：北端 4 卧室（每户 2 间）→ 厨卫带（最西/最东，各有窗）→ 南部客厅 + 楼梯间
// 楼梯间南中入户，进户左转第一跑，第二跑压在入口上方；东侧 0.8m 走道通北端两户门

export const MODEL = { W: 12.6, L: 13.0, storey: 3.0, wallH: 2.85, slab: 0.15, TE: 0.24, TI: 0.12 };

const r2 = (v) => +v.toFixed(2);
const area = (r) => r2((r[2] - r[0]) * (r[3] - r[1]));
const mirror = ([x0, y0, x1, y1]) => [r2(12.6 - x1), y0, r2(12.6 - x0), y1];
const mirrorPt = ([x, y]) => [r2(12.6 - x), y];

// ---------- 房间（净空矩形；可多矩形并集，如客厅+餐厅开敞相连） ----------
const W_LIV = [0.24, 0.24, 4.94, 5.0];      // 客厅（可作客卧）
const W_DIN = [2.46, 4.9, 6.24, 9.04];      // 餐厅（与客厅开敞，中部无墙）
const W_KIT = [0.24, 5.06, 2.34, 7.54];     // 厨房（最西，带窗）
const W_BTH = [0.24, 7.66, 2.34, 9.04];     // 卫生间（最西，带窗）
const W_B1 = [0.24, 9.16, 3.44, 12.76];     // 卧室1
const W_B2 = [3.56, 9.16, 6.24, 12.76];     // 卧室2（至中墙）
const HALL = [5.06, 0.24, 7.54, 4.94];      // 楼梯间（含 0.8m 东走道）

export const SPACES = [
  { id: 'livW', name: '客厅+餐厅(可作客卧)', en: 'LIVING/DINING W', type: 'living', rects: [W_LIV, W_DIN], doors: [[4.8, 4.4]] },
  { id: 'kitW', name: '厨房 W', en: 'KITCHEN W', type: 'kitchen', rects: [W_KIT], doors: [[2.3, 6.15]] },
  { id: 'bthW', name: '卫生间 W', en: 'BATH W', type: 'bath', rects: [W_BTH], doors: [[2.3, 8.4]] },
  { id: 'bed1W', name: '卧室1 W', en: 'BEDROOM 1', type: 'bed2', rects: [W_B1], doors: [[2.95, 9.3]] },
  { id: 'bed2W', name: '卧室2 W', en: 'BEDROOM 2', type: 'bed2', rects: [W_B2], doors: [[4.9, 9.3]] },
  { id: 'hall', name: '楼梯间', en: 'STAIR HALL', type: 'hall', rects: [HALL], doors: [[6.05, 0.4]] },
  { id: 'livE', name: '客厅+餐厅(可作客卧)', en: 'LIVING/DINING E', type: 'living', rects: [mirror(W_LIV), mirror(W_DIN)], doors: [mirrorPt([4.8, 4.4])], mir: true },
  { id: 'kitE', name: '厨房 E', en: 'KITCHEN E', type: 'kitchen', rects: [mirror(W_KIT)], doors: [mirrorPt([2.3, 6.15])], mir: true },
  { id: 'bthE', name: '卫生间 E', en: 'BATH E', type: 'bath', rects: [mirror(W_BTH)], doors: [mirrorPt([2.3, 8.4])], mir: true },
  { id: 'bed3E', name: '卧室3 E', en: 'BEDROOM 3', type: 'bed2', rects: [mirror(W_B2)], doors: [mirrorPt([4.9, 9.3])], mir: true },
  { id: 'bed4E', name: '卧室4 E', en: 'BEDROOM 4', type: 'bed2', rects: [mirror(W_B1)], doors: [mirrorPt([2.95, 9.3])], mir: true },
];

export const spaceArea = (s) => r2(s.rects.reduce((a, r) => a + area(r), 0) - overlap(s.rects));
const overlap = (rs) => (rs.length < 2 ? 0 : r2(Math.max(0, Math.min(rs[0][2], rs[1][2]) - Math.max(rs[0][0], rs[1][0])) * Math.max(0, Math.min(rs[0][3], rs[1][3]) - Math.max(rs[0][1], rs[1][1]))));

// ---------- 家具生成器：房间局部坐标 [0..W, 0..D]，doorSpan 为门洞在该房边上的区间 ----------
const P = (name, x, y, w, d, h, use, kind) => ({ name, x, y, w, d, h, use, kind });

// 卧室（双人）：床靠北墙居中，床头柜两侧，衣柜/书桌在门侧的南墙空档
function furnBed2(W, D, doorSpan) {
  const bx = (W - 1.5) / 2;
  const list = [
    P('双人床 1.5×2.0', bx, D - 2.0, 1.5, 2.0, 0.5, [0, -1], 'bed'),
    P('床头柜 0.4×0.4', Math.max(0, bx - 0.45), D - 0.4, 0.4, 0.4, 0.5, [0, -1], 'nightstand'),
    P('床头柜 0.4×0.4', Math.min(W - 0.4, bx + 1.55), D - 0.4, 0.4, 0.4, 0.5, [0, -1], 'nightstand'),
  ];
  const d0 = doorSpan ? doorSpan[0] : W / 2, d1 = doorSpan ? doorSpan[1] : W / 2 + 0.1;
  // 南墙（y=0）上避开门洞的空档
  const gaps = [];
  if (d0 > 0.05) gaps.push([0, d0]);
  if (W - d1 > 0.05) gaps.push([d1, W]);
  gaps.sort((a, b) => (b[1] - b[0]) - (a[1] - a[0]));
  if (gaps[0] && gaps[0][1] - gaps[0][0] >= 0.6) {
    const w = Math.min(1.4, gaps[0][1] - gaps[0][0]);
    list.push(P(`衣柜 ${r2(w)}×0.6`, gaps[0][0], 0.1, w, 0.6, 2.2, [0, 1], 'wardrobe'));
  }
  if (gaps[1] && gaps[1][1] - gaps[1][0] >= 0.5) {
    const w = Math.min(1.0, gaps[1][1] - gaps[1][0]);
    list.push(P(`书桌 ${r2(w)}×0.5`, gaps[1][0], 0.1, w, 0.5, 0.75, [0, 1], 'desk'));
  }
  return list;
}

function furnLiving(W, D) {
  return [
    P('三人沙发 2.1×0.85', 0.24, 1.3, 0.85, 2.1, 0.8, [1, 0], 'sofa'),
    P('茶几 1.1×0.55', 1.5, 1.6, 1.1, 0.55, 0.45, [0, 0], 'table'),
    P('电视柜 1.6×0.4', 3.3, 1.3, 0.4, 1.6, 0.45, [-1, 0], 'cabinet'),
    P('餐桌 1.4×0.8(含椅)', 3.2, 6.0, 1.88, 1.3, 0.75, [0, 0], 'table'),
    P('餐边柜 1.2×0.4', 5.8, 6.4, 0.4, 1.2, 0.8, [-1, 0], 'cabinet'),
    P('冰柜/备餐台 0.8×0.5', 2.5, 7.9, 0.8, 0.5, 0.8, [0, -1], 'cabinet'),
  ];
}
function furnKitchen(W, D) {
  return [
    P('L形操作台 0.6×2.3', 0, 0.18, 0.6, 2.3, 0.85, [1, 0], 'counter'),
    P('操作台(北) 1.0×0.6', 0.6, D - 0.6, 1.0, 0.6, 0.85, [0, -1], 'counter'),
    P('冰箱 0.65×0.7', W - 0.7, 0.1, 0.7, 0.65, 1.8, [0, 1], 'fridge'),
  ];
}
function furnBath(W, D) {
  return [
    P('淋浴 0.9×0.9', 0, 0, 0.9, 0.9, 0.1, [1, 0], 'shower'),
    P('坐便器 0.4×0.7', 0.95, D - 0.7, 0.4, 0.7, 0.75, [0, -1], 'toilet'),
    P('洗手台 0.5×0.4', 1.5, D - 0.4, 0.5, 0.4, 0.8, [0, -1], 'basin'),
  ];
}
function furnHall() {
  return [
    P('双跑楼梯 U 形(实体)', 5.06, 1.1, 1.68, 2.66, 3.0, [0, 0], 'stair'),
    P('鞋柜 0.35×0.8', 5.1, 0.28, 0.35, 0.8, 1.0, [1, 0], 'cabinet'),
    P('换鞋凳 0.8×0.35', 6.9, 3.6, 0.35, 0.8, 0.45, [-1, 0], 'cabinet'),
  ];
}

// 门洞区间（房间局部坐标所在边）：卧室门在南墙，厨卫门在东/西内墙
function doorSpanOf(space) {
  const r = space.rects[0];
  const W = r[2] - r[0], D = r[3] - r[1];
  const dp = space.doors[0];
  return [r2(dp[0] - r[0] - 0.4), r2(dp[0] - r[0] + 0.4)]; // 门宽约 0.8~0.9 居中于门点
}

export function furnitureOf(space) {
  const r = space.rects[0];
  const W = r2(r[2] - r[0]), D = r2(r[3] - r[1]);
  let list;
  if (space.type === 'bed2') list = furnBed2(W, D, doorSpanOf(space));
  else if (space.type === 'kitchen') list = furnKitchen(W, D);
  else if (space.type === 'bath') list = furnBath(W, D);
  else if (space.type === 'hall') return furnHall();
  else {
    // 客厅为西户绝对坐标（L 形），东户镜像
    const abs = furnLiving(W, D);
    return space.mir ? abs.map((q) => ({ ...q, x: r2(12.6 - q.x - q.w), use: [-q.use[0], q.use[1]] })) : abs;
  }
  // 局部 → 世界（东户镜像）
  return list.map((q) => {
    if (!space.mir) return { ...q, x: r2(r[0] + q.x), y: r2(r[1] + q.y) };
    return { ...q, x: r2(r[2] - q.x - q.w), y: r2(r[1] + q.y), use: [-q.use[0], q.use[1]] };
  });
}

export const FURN_COLORS = {
  sofa: 0x6f8fbf, table: 0xb08a5a, cabinet: 0xa8845a, bed: 0xc9a06a, nightstand: 0xb08a5a,
  wardrobe: 0x8f7a5f, desk: 0xb08a5a, counter: 0xd8d8d8, fridge: 0xcccccc, basin: 0xdde8ee,
  toilet: 0xe8eef2, shower: 0xbfe0e8, stair: 0xb8bcc2,
};

// ---------- 指标限值（GB 50096 住宅设计规范 / GB 50016 建筑设计防火规范 / 人体工学经验值） ----------
export const LIMITS = {
  riserMax: 0.175, goingMin: 0.26, comfort: [600, 640],
  flightMin: 0.75, flightComfort: 0.9, landingMin: 0.9,
  corridorMin: 0.9, corridorAbs: 0.6,
  doorEntry: 1.0, doorRoom: 0.8,
  clearHMin: 2.4, stairHead: 2.0, balustrade: 0.9,
  furniturePath: 0.6, kitchenPath: 0.9,
  winFloorRatio: 1 / 7,
  bed2Area: 9, livingArea: 10, kitchenArea: 4, bathArea: 3,
  carSpace: [2.5, 5.3],
};

// ---------- 通行路径（3D 人体净空模拟；z 为脚面标高） ----------
export const PATHS = [
  {
    id: 'p1', name: '入户 → 左转上楼 → 二层',
    desc: '进南门左手第一跑起步（无需单独通道，与第二跑投影重叠），北端平台折返后压着入口上方上到二层',
    pts: [
      [6.05, 0.4, 0], [5.5, 1.0, 0], [5.48, 1.2, 0.19], [5.48, 1.5, 0.47], [5.48, 1.8, 0.75],
      [5.48, 2.1, 1.03], [5.48, 2.4, 1.31], [5.48, 2.7, 1.5], [5.7, 3.3, 1.5], [6.3, 3.3, 1.5],
      [6.3, 2.7, 1.69], [6.3, 2.4, 1.96], [6.3, 2.1, 2.24], [6.3, 1.8, 2.52], [6.3, 1.5, 2.79], [6.3, 1.2, 3.0],
      [6.3, 0.7, 3.0],
    ],
  },
  {
    id: 'p2', name: '入户 → 东侧走道 → 东户门',
    desc: '楼梯间东侧 0.80m 走道直达北端右户门（门洞 0.90m）',
    pts: [[6.05, 0.4, 0], [6.9, 0.6, 0], [7.14, 1.0, 0], [7.14, 3.5, 0], [7.14, 4.4, 0], [8.2, 4.4, 0]],
  },
  {
    id: 'p3', name: '入户 → 北端 → 西户门',
    desc: '北端折向西到左户门；校核楼梯尾段与门垛的间距',
    pts: [[6.05, 0.4, 0], [6.9, 0.6, 0], [7.14, 3.8, 0], [6.6, 4.4, 0], [5.4, 4.4, 0], [4.6, 4.4, 0]],
  },
  {
    id: 'p4', name: '东户：客厅 → 餐厅 → 厨房',
    desc: '户内主要活动线（家具搬运 / 轮椅通行校核）',
    pts: [[8.6, 4.4, 0], [9.2, 3.2, 0], [8.8, 1.6, 0], [8.2, 3.2, 0], [8.6, 5.6, 0], [8.6, 7.2, 0], [9.8, 6.5, 0], [10.4, 6.15, 0]],
  },
];
