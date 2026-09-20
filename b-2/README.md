# B-2｜北方农村双户两层住宅

**主文档：[设计与施工准备说明 R1](design/设计与施工准备说明.md)**

本版以低成本入住、两层各两户、未来低成本合户、明装可维护管线、防潮保温为目标。固定面宽12.6m，总进深19m；当前保留13m房屋+1m北退让+5m南院。

## 文件入口

| 文件/目录 | 用途 |
|---|---|
| `design/设计与施工准备说明.md` | 详细方案、尺寸、分期、节点、施工顺序、验收与待定事项 |
| `design/figures/*.svg` | 中文可编辑矢量图，普通浏览器可打开 |
| `design/parameters.json` | 建模使用的主要概念参数与待确认状态 |
| `models/01_site_drainage.blend` | 场地坡向、入口、集水与排水条件 |
| `models/02_two_households.blend` | 修改后的一层、二层及楼梯平台；默认爆炸分层展示 |
| `models/03_exposed_services.blend` | 四户与公共部分的管线、供暖路径示意 |
| `models/04_envelope_roof.blend` | 全高墙、外维护与简单双坡屋面示意 |
| `models/05_future_merge.blend` | 两层预留连接口打开后的合户示意 |
| `previews/*.png` | 各阶段渲染图及原方案参考 |
| `scripts/build_stages.py` | 从保留的原模型重建阶段文件的 Blender Python 脚本 |
| `scripts/make_figures.py` | 重新生成中文SVG图 |
| `scripts/validate_assets.py` | 检查链接、模型阶段清单、尺寸总和和资产哈希 |
| `asset_manifest.json` | 输出资产大小、SHA-256与检查结果 |
| `b-2.jpg` | 用户原始草图 |
| `b-2_model.blend` | 上一版一层概念模型，保留不覆盖 |

## 如何编辑

1. 先打开 `models/02_two_households.blend`。二层默认上移5m展示，实际层高关系在对象与集合自定义属性中记录；脚本中 `display_explode_m` 指明展示偏移。**不可从爆炸展示直接量建筑总高。**
2. `L1_`、`L2_` 分别为两层集合；`MERGE_INFILL` 是将来拆除的非承重填充。
3. `Upper walls` 集合默认关闭，用于剖切；全高展示见阶段04。
4. 阶段03管线是路线示意，没有管径计算和坡度设计；阶段01地形是坡向示意，没有替代实测标高。
5. 改 `design/parameters.json` 后运行建模脚本；脚本以原一层模型为基底，仅支持脚本明示的参数。宽度、总进深或原始房间分区大改仍需同步修改原模型，不能仅改JSON自动重排。

## 重建

在 Blender 的 Scripting 工作区执行：

```python
exec(compile(open('/media/code/tools/building/b-2/scripts/build_stages.py', encoding='utf-8').read(), 'build_stages.py', 'exec'))
```

也可用同版本 Blender 后台执行（本版验证版本3.6.23）：

```bash
blender --background --python scripts/build_stages.py
python3 scripts/make_figures.py
python3 scripts/validate_assets.py
```

重建会更新 `models/`、`previews/` 和清单，先提交或另存手工修改的阶段文件。原始 `b-2_model.blend` 不会被脚本覆盖。

## Git

沿用上级 `/media/code/tools/building` 已有仓库。本次范围限 `b-2`。可编辑 `.blend`、脚本、参数、Markdown、SVG及预览均实际入库；文件规模较小，采用普通Git二进制跟踪，无外部LFS依赖。旧的已跟踪 `b-2_model.blend1` 原样保留，新产生备份忽略。

```bash
git -C /media/code/tools/building status --short -- b-2
git -C /media/code/tools/building log --oneline -- b-2
git -C /media/code/tools/building diff -- b-2/design b-2/scripts
```

### 尺寸与施工状态

本版为设计深化与施工交底准备资料。已知边界、暂定尺寸、必须测量/设计的项目在主文档分别标记。基础、挡土、抗震、配筋、梁柱、最终雨污出口和供暖容量需由当地有相应能力的人员依据现场确定，文档不编造这些数值。
