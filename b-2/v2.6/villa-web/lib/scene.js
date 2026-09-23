// three.js 场景：几何来自 Blender 导出的 model.json（盒体汤 + 对象矩阵），坐标保持 Blender 约定（Z 向上）
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { furnitureOf, SPACES, PATHS } from './specs';

function makeMat(name, color) {
  const m = new THREE.MeshStandardMaterial({ color: new THREE.Color(...color), roughness: 0.85, metalness: 0.0 });
  if (/glass/.test(name)) { m.transparent = true; m.opacity = 0.3; m.color = new THREE.Color(0.63, 0.82, 0.9); m.roughness = 0.1; }
  if (/demo/.test(name)) m.color = new THREE.Color(0.95, 0.8, 0.15);
  if (/leaf|frame|door/.test(name)) m.color = new THREE.Color(0.55, 0.37, 0.2);
  if (/cap|cop/.test(name)) m.color = new THREE.Color(0.72, 0.18, 0.12);
  if (/guard|rail/.test(name)) { m.transparent = /guard/.test(name) && !/rail/.test(name); m.opacity = 0.35; m.color = new THREE.Color(0.75, 0.8, 0.85); }
  if (/paving|road|drive/.test(name)) m.color = new THREE.Color(0.6, 0.6, 0.58);
  return m;
}

function labelSprite(text, color = '#1a3a5c') {
  const cv = document.createElement('canvas');
  const pad = 8, fs = 34;
  const ctx = cv.getContext('2d');
  ctx.font = `600 ${fs}px "Noto Sans CJK SC", "Microsoft YaHei", sans-serif`;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2;
  cv.width = w; cv.height = fs + pad * 2;
  const c2 = cv.getContext('2d');
  c2.font = `600 ${fs}px "Noto Sans CJK SC", "Microsoft YaHei", sans-serif`;
  c2.fillStyle = 'rgba(255,255,255,0.85)';
  c2.fillRect(0, 0, cv.width, cv.height);
  c2.fillStyle = color;
  c2.textBaseline = 'middle';
  c2.fillText(text, pad, cv.height / 2);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sp.scale.set((cv.width / cv.height) * 0.45, 0.45, 1);
  return sp;
}

const FURN_COLORS = {
  sofa: 0x6f8fbf, table: 0xb08a5a, cabinet: 0xa8845a, bed: 0xc9a06a, nightstand: 0xb08a5a,
  wardrobe: 0x8f7a5f, desk: 0xb08a5a, counter: 0xd8d8d8, fridge: 0xcccccc, basin: 0xdde8ee,
  toilet: 0xe8eef2, shower: 0xbfe0e8, stair: 0xc0c0c0,
};

export function createScene(container, data) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0.12, 0.14, 0.17);

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 500);
  camera.up.set(0, 0, 1);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxPolarAngle = Math.PI * 0.495;

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.6);
  sun.position.set(-20, -25, 35);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xbcd4ff, 0.5);
  fill.position.set(25, 15, 10);
  scene.add(fill);

  // 分组：一层 / 二层 / 屋面（错层爆炸用）
  const groups = {
    f1: new THREE.Group(), f2: new THREE.Group(), roof: new THREE.Group(),
    furn: new THREE.Group(), labels: new THREE.Group(), walk: new THREE.Group(),
  };
  for (const k of Object.keys(groups)) scene.add(groups[k]);

  const pickables = [];   // 模型盒体（射线检测）
  const frameHolders = []; // 参与取景的构件（排除大地/道路等场地元素）
  const SITE_RE = /ground|road|drive|paving|plinth/;
  const allMats = new Set();
  for (const o of data.objects) {
    const mat = makeMat(o.name + ' ' + (o.mat || ''), o.color || [0.8, 0.8, 0.8]);
    allMats.add(mat);
    const M = new THREE.Matrix4().set(...o.m);
    const holder = new THREE.Group();
    holder.name = o.name;
    holder.matrixAutoUpdate = false;
    holder.matrix.copy(M);
    if (!SITE_RE.test(o.name)) frameHolders.push(holder);
    for (const b of o.boxes) {
      const [x0, y0, z0, x1, y1, z1] = b;
      const g = new THREE.BoxGeometry(Math.max(0.01, x1 - x0), Math.max(0.01, y1 - y0), Math.max(0.01, z1 - z0));
      const mesh = new THREE.Mesh(g, mat);
      mesh.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
      mesh.userData.objName = o.name;
      holder.add(mesh);
      pickables.push(mesh);
    }
    groups[o.g].add(holder);
  }

  // 标签（按层分组，随爆炸偏移）
  const labelsG = { f1: new THREE.Group(), f2: new THREE.Group() };
  for (const l of data.labels) {
    const sp = labelSprite(l.t.replace(/\n/g, ' '));
    sp.position.set(...l.loc);
    (labelsG[l.g] || labelsG.f1).add(sp);
  }
  groups.labels.add(labelsG.f1, labelsG.f2);

  // 家具（两层同布局；二层随爆炸偏移）
  const furnMeshes = [];
  const furnL = { f1: new THREE.Group(), f2: new THREE.Group() };
  groups.furn.add(furnL.f1, furnL.f2);
  for (const s of SPACES) {
    for (const f of furnitureOf(s)) {
      if (f.kind === 'stair') continue; // 实体楼梯已有几何
      for (const [zi, zBase] of [[0, 0], [1, 3.0]]) {
        const g = new THREE.BoxGeometry(f.w, f.d, f.h);
        const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: FURN_COLORS[f.kind] || 0x999999, roughness: 0.7, transparent: true, opacity: 0.92 }));
        m.position.set(f.x + f.w / 2, f.y + f.d / 2, zBase + f.h / 2);
        m.userData = { furniture: f.name, space: s.id };
        (zi ? furnL.f2 : furnL.f1).add(m);
        furnMeshes.push(m);
      }
    }
  }
  groups.furn.visible = false;

  // 通行人形（0.22 半径肩宽，1.75m 高）
  const figMat = new THREE.MeshStandardMaterial({ color: 0x35d07f, transparent: true, opacity: 0.75 });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 1.55, 20), figMat);
  body.rotation.x = Math.PI / 2; // cylinder 默认沿 Y，本场景 Z 向上
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 12), figMat);
  head.position.z = 1.62;
  const fig = new THREE.Group();
  fig.add(body, head);
  body.position.z = 0.775;
  fig.visible = false;
  groups.walk.add(fig);

  const raycaster = new THREE.Raycaster();
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  let clipOn = false;

  function setUp(x, y, z) {
    const dir = new THREE.Vector3(0, 0, 1);
    raycaster.set(new THREE.Vector3(x, y, z), dir);
    raycaster.far = 30;
    const hits = raycaster.intersectObjects(pickables, false);
    return hits.length ? hits[0].point.z : Infinity;
  }
  function sideDist(x, y, z, dx, dy) {
    raycaster.set(new THREE.Vector3(x, y, z), new THREE.Vector3(dx, dy, 0).normalize());
    raycaster.far = 8;
    const hits = raycaster.intersectObjects(pickables, false);
    return hits.length ? hits[0].distance : Infinity;
  }

  // 沿路径采样净空：headroom = 脚面到顶的距离；side = 四向侧距
  function samplePath(pts) {
    const out = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const a = pts[i], b = pts[i + 1];
      const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const n = Math.max(1, Math.ceil(d / 0.12));
      for (let t = 0; t < n; t++) {
        const u = t / n;
        const x = a[0] + (b[0] - a[0]) * u, y = a[1] + (b[1] - a[1]) * u, z = a[2] + (b[2] - a[2]) * u;
        const top = setUp(x, y, z + 0.02);
        const headroom = top === Infinity ? 9 : +(top - z - 0.02).toFixed(2);
        const s = [sideDist(x, y, z + 1.4, 1, 0), sideDist(x, y, z + 1.4, -1, 0), sideDist(x, y, z + 1.4, 0, 1), sideDist(x, y, z + 1.4, 0, -1)];
        out.push({ x, y, z, headroom, side: +Math.min(...s).toFixed(2) });
      }
    }
    return out;
  }

  // ---------- 相机预设 ----------
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const presets = {
    god: { pos: V(22, -24, 27), tgt: V(16, 4, 1.5) },
    home: { pos: V(24, -30, 32), tgt: V(6.3, 5, 1.5) },
    f1: { pos: V(14, -18, 19), tgt: V(6.3, 6.5, 0.5) },
    plan: { pos: V(6.3, 6.5, 34), tgt: V(6.3, 6.5, 0) },
    stair: { pos: V(9.5, -3.5, 5.5), tgt: V(5.9, 2.4, 1.5) },
  };
  function setPreset(k) {
    const p = presets[k]; if (!p) return;
    camera.position.copy(p.pos);
    controls.target.copy(p.tgt);
    controls.update();
  }
  setPreset('god');

  // 取景：按可见的建筑构件包围盒定相机距离与目标（保持当前视角方向）
  function frameAll() {
    const box = new THREE.Box3();
    for (const h of frameHolders) {
      let p = h, vis = true;
      while (p) { vis = vis && p.visible; p = p.parent; }
      if (vis) box.expandByObject(h);
    }
    if (box.isEmpty()) return;
    const c = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const rad = Math.max(size.x * 0.5, size.y * 0.5, size.z) * 0.72 + 1.5;
    const dist = (rad / Math.tan((camera.fov * Math.PI) / 360)) * 1.15;
    const dir = camera.position.clone().sub(controls.target).normalize();
    if (dir.lengthSq() < 0.5) dir.set(0.5, -0.6, 0.62).normalize();
    controls.target.copy(c);
    camera.position.copy(c.clone().add(dir.multiplyScalar(dist)));
    controls.update();
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();

  let raf = 0, walkSamples = null, walkT = 0, walking = false, onWalkTick = null;
  function loop() {
    raf = requestAnimationFrame(loop);
    if (walking && walkSamples) {
      walkT += 1.1;
      const i = Math.min(walkSamples.length - 1, Math.floor(walkT));
      const s = walkSamples[i];
      fig.position.set(s.x, s.y, s.z);
      fig.visible = true;
      figMat.color.set(s.headroom >= 2.0 && s.side >= 0.3 ? 0x35d07f : 0xe05535);
      if (onWalkTick) onWalkTick(s, i / (walkSamples.length - 1));
      if (i >= walkSamples.length - 1) walking = false;
    }
    controls.update();
    renderer.render(scene, camera);
  }
  loop();

  window.addEventListener('resize', resize);
  scene.updateMatrixWorld(true); // 射线净空实测前必须先更新世界矩阵
  frameAll();

  return {
    frameAll,
    THREE, scene, camera, renderer, controls, groups,
    setPreset,
    setExplode(t) {
      groups.f2.position.x = 15.5 * t;
      groups.roof.position.x = 31 * t;
      labelsG.f2.position.x = 15.5 * t;
      furnL.f2.position.x = 15.5 * t;
      scene.updateMatrixWorld(true);
      frameAll();
    },
    setVis(v) {
      groups.f1.visible = !!v.f1; groups.f2.visible = !!v.f2; groups.roof.visible = !!v.roof;
      groups.labels.visible = !!v.labels; groups.furn.visible = !!v.furn;
    },
    setSection(y) {
      clipOn = y != null;
      clipPlane.constant = -(y ?? 0);
      for (const m of allMats) { m.clippingPlanes = clipOn ? [clipPlane] : null; m.needsUpdate = true; }
      for (const m of furnMeshes) { m.material.clippingPlanes = clipOn ? [clipPlane] : null; m.material.needsUpdate = true; }
    },
    pick(clientX, clientY) {
      const r = renderer.domElement.getBoundingClientRect();
      const nd = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
      raycaster.setFromCamera(nd, camera);
      raycaster.far = 500;
      const hits = raycaster.intersectObjects(pickables, false);
      return hits.length ? { name: hits[0].object.userData.objName, point: hits[0].point } : null;
    },
    probeGround(clientX, clientY) {
      const r = renderer.domElement.getBoundingClientRect();
      const nd = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
      raycaster.setFromCamera(nd, camera);
      raycaster.far = 500;
      const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
      const p = new THREE.Vector3();
      return raycaster.ray.intersectPlane(plane, p) ? p : null;
    },
    headroomAt: (x, y, z) => { const t = setUp(x, y, z + 0.02); return t === Infinity ? 9 : +(t - z - 0.02).toFixed(2); },
    samplePath,
    playWalk(pathId, tick) {
      const path = PATHS.find((p) => p.id === pathId) || PATHS[0];
      walkSamples = samplePath(path.pts);
      walkT = 0; walking = true; onWalkTick = tick;
    },
    stopWalk() { walking = false; fig.visible = false; },
    measureFrom: null,
    dispose() { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); renderer.dispose(); },
  };
}
