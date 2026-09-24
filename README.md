# 暮光浮岛 · Living Island

基于已有 `island_dusk_refined.blend` 持续制作的可玩浮岛：视觉校准、种植订单、昼夜天气和远景群岛，并加入扩岛与主角自主生活。使用本机 Blender 5.2.1 制作资产，Three.js 本地运行。

当前可编辑场景：[建筑精修版 Blender](assets/architecture/island_architecture.blend)。[主视角渲染](renders/architecture/hero.png) · [住宅近景](renders/architecture/house_detail.png) · [咖啡厅近景](renders/architecture/cafe_detail.png)。此前坡地与树木版、参考布局版、扩建版和视觉校准版保留。

## 打开体验

双击 `start_viewer.command`，或者在项目根目录运行：

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

打开 [动态小岛](http://127.0.0.1:8765/viewer/)。页面默认观景，点击「进入小岛」开始游玩。

新增 **建筑近景精修**：住宅细窗格、弯曲窗框、入口瓦檐和白粉花藤；咖啡厅统一木瓦色系，补上格窗、曲面布伞和桌面杯碟。建筑独立使用木石与织物纹理，网页保留法线质感。现有布局、树木、日程和存档延续。见 [素材说明](assets/architecture/README.md) 与 [近景及前后对照](http://127.0.0.1:8765/renders/architecture/comparison.html)。

新增 **坡地与树丛**：后方抬起林间坡地，住宅前有缓坡，溪水从高处沿原有河湾下行；岸边加入浅水石、苔藓和芦草。岛缘增加不规则岩块、花草与垂藤，瀑布加入水帘和渐隐。树木从 11 棵增加到 26 棵，原来的粉色花树恢复在住宅右侧，中央休闲区保持开放。见 [本轮说明](assets/landscape/README.md) 与 [画面对照](http://127.0.0.1:8765/renders/landscape/comparison.html)。

新增 **参考布局重组**：住宅左上、菜园和羊圈左侧下方、咖啡馆右上、桥右下。中央连贯草地和石径留出休闲区；溪流从偏左上入口转弯，经过横向河湾后流向右下瀑布，水宽由约 1.6 米渐增至 6.8 米。建筑保持原尺寸，河岸花丛、树冠、石块和步道重新布置。碰撞、过桥寻路、灯光、雨棚和日程地点同步更新，旧存档进度保留。详见 [当前布局说明](assets/layout/README.md)。

已有 **自在生活**：观景时雏菊按时段散步、照料花草，夜间回廊下休息，下雨找雨棚。点击「看看她」跟随，「进入小岛」从当前位置接管，退出后恢复自主生活。日记包含果园和溪边目的地；窄屏日记可以收起。自主动作目前只作生活演出，不改动物品和作物。此前等比例扩建的记录见 [扩建与日程说明](assets/expanded/README.md)。

新增 **云上时光**：点击右上角时钟，可选择清晨、正午、黄昏和夜晚，拖动全天时间滑块，暂停或以 0.5 / 1 / 4 倍速运行。默认 30 分钟走过一天；选择时段会暂停时间，风景仍然活动。天气提供晴天、多云、薄雾和小雨，切换时平滑过渡。12 座三维远岛与云海围绕主岛，夜间窗灯、路灯和萤火虫亮起。说明见 [昼夜与群岛](assets/world/README.md)。

新增 [人物工作室](http://127.0.0.1:8765/viewer/character.html)：默认展示依据参考图生成的 Tripo 精细版，并保留本地 Blender 初版对照。精细版保留 4K PBR 纹理，经本地 Blender 减面、修正蒙皮和制作五段动作后接入游戏，包含 37 根骨骼。高精度原模、可编辑文件与制作说明见 [精细人物说明](assets/character_tripo/README.md)。面部特写、手指与步态仍有精修空间。

- **移动**：WASD / 方向键，Shift 快走；也可以点击地面、菜田标签，或日记里的目的地按钮自动步行。
- **互动**：走近目标，按 E 或点击互动按钮。菜田依次播种、浇水，18 秒后收获。
- **订单**：收集 3 份蔬菜，经过石桥前往咖啡馆，在门前交付，获得 30 金币；可重复种植和交付。
- **小猫**：走近后可以抚摸。
- **镜头**：观景时左键拖动；漫游时右键拖动，滚轮缩放。触屏点击行走、双指调整视角。Esc 退出漫游。
- **保存**：作物、收获、金币、订单和位置自动保存在当前浏览器；离线期间作物继续生长。「重新开始」会先显示确认对话框。
- **画面**：可以暂停风景，或切换流畅画质。暂停风景会暂停环境和角色，作物计时继续。系统开启减少动态效果时，初次加载默认暂停。
- **世界时间**：仅在页面可见且风景运行时推进；关闭页面后停留在保存的时刻。时间、日期、流速与天气单独保存，不改动种植存档。暂停时间仅冻结昼夜，暂停风景会同时冻结环境动画与昼夜。

[当前地形与树木对照](http://127.0.0.1:8765/renders/landscape/comparison.html) · [上一轮布局对照](http://127.0.0.1:8765/renders/layout/comparison.html) · [早期三阶段对照](http://127.0.0.1:8765/renders/living/comparison.html) · [上一版静态查看器](http://127.0.0.1:8765/viewer/static.html)

## 此前主岛视觉校准

- 屋檐以上的主屋高度压缩到原来的 69%，保留双山墙、瓦片、窗户与烟囱；主镜头降低俯视角度。
- 岛体 10.1 米以下的高度差缩放至 73%，根系、垂藤与瀑布同步调整，减轻岩壁厚重感。
- 地表、路径和水体采用连续弯曲变形，建筑与主要独立物件平移保持形体；桥位保留，花丛使用固定种子的疏密变化。
- 网页水体使用流动着色，增加沿河水光、下落水滴、瀑布薄雾、炊烟和少量萤火；植被微摆，小船船体绕悬点摆动，支架保持静止，绳索随船连接。
- 场景文件保留原先拆分的草帽女孩；网页隐藏原人物，单独载入 `assets/character_tripo/runtime/daisy_tripo.glb`，通过骨骼动画播放待机、行走和农活动作。人物、六组作物、小船、水体、猫和羊保留控制节点。
- 使用地面高度函数、障碍范围与网格寻路实现移动。房屋、菜田围栏、河水与岛缘阻挡角色；桥为跨河通路。观景无需进入游戏。

## 交付文件

| 文件 | 用途 |
| --- | --- |
| `assets/architecture/island_architecture.blend` / `.glb` | 当前建筑精修源文件和网页减面版 |
| `assets/architecture/scene.json` / `textures/` | 当前场景配置与建筑独立纹理 |
| `scripts/crafted_architecture.py` / `refine_architecture.py` | 本轮建筑细部、材质与导出 |
| `renders/architecture/` / `reports/architecture_*` | 建筑近景、前后对照和验证结果 |
| `assets/landscape/island_landscape.blend` / `.glb` | 保留的坡地、河岸与树木版源文件和网页模型 |
| `assets/landscape/scene.json` | 上一版起伏高度、河道、轮廓、碰撞和生活地点 |
| `scripts/refine_landscape.py` / `landscape_spec.py` | 本轮地形与树木构建、共享高度参数 |
| `scripts/test_landscape.mjs` / `validate_landscape.cjs` | 地形高度、树木、水流与模型验证 |
| `assets/layout/island_layout.blend` / `.glb` | 保留的前一版参考布局场景 |
| `assets/layout/scene.json` | 前一版曲线河道、碰撞、生活地点与雨棚范围 |
| `scripts/recompose_island.py` / `layout_spec.py` | 当前布局构建与共享地形定义 |
| `scripts/test_layout.mjs` / `validate_layout.cjs` | 新布局路径、日程、迁移和模型验证 |
| `assets/expanded/island_expanded.blend` / `.glb` | 保留的前一版扩建场景 |
| `assets/expanded/scene.json` | 前一版碰撞、日程地点和雨棚范围 |
| `viewer/resident.mjs` | 观景自主生活及手动接管 |
| `scripts/expand_island.py` | 从动态版构建扩岛 |
| `scripts/test_resident.mjs` | 扩岛、路径、日程与迁移测试 |
| `island_dusk_living.blend` | 扩建前的动态版场景，保留独立物件与人物关节部件 |
| `island_dusk_living.glb` | 扩建前网页版本，415,151 三角面、18,163,780 字节 |
| `assets/living/scene.json` | 物体节点、菜田、桥、障碍、出生点和环境发射点 |
| `viewer/living.js` | 场景加载、人物移动、镜头、互动和 UI |
| `viewer/environment.js` | 实时水体、植被、粒子、小船和羊的动态 |
| `viewer/navigation.mjs` | 可走范围、地面高度、寻路与连续碰撞步进 |
| `viewer/game-state.mjs` | 种植、成长、收获、订单和存档 |
| `scripts/prepare_living.py` | 从精修版重现视觉校准、拆分、渲染和网页导出 |
| `scripts/test_living.mjs` | 种植订单、存档、路径可达性及碰撞测试 |
| `scripts/validate_living.cjs` | glTF 校验、控制节点和文件预算检查 |
| `renders/living/` | 1920×1440 离线渲染与三阶段对照页 |
| `reports/living_*.json` | 实测模型规格、格式校验和逻辑测试结果 |

前两版 `.blend` / `.glb` 保留。之前精修版的说明保存在 `reference/refined_readme.md`，初版说明在 `reference/baseline_readme.md`。

## 重现与验证

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/prepare_living.py -- --render --width 1920 --samples 64
node scripts/test_living.mjs
# 需要可解析的 gltf-validator 包，或通过 GLTF_VALIDATOR_MODULE 指定安装路径：
node scripts/validate_living.cjs
```

生成脚本只读取上一版精修文件，写入本轮独立文件；固定随机种子，可重复运行。静态环境合批，动态节点保留；旧的法线压缩器仅压缩顶点法线并移除不用的 UV，动画由网页实时计算。

## 当前范围

这是可玩的单人原型，尚未逐像素匹配原参考图。建筑细部、植被自然度、岩体和实时光照仍有差异；离线渲染展示成熟作物，网页按当前种植状态显示。

扩岛与自主生活基础已完成；坐姿、饮茶、室内睡眠、离线自主生活尚未实现。环境和游戏逻辑运行在网页中，场景 `.blend` 提供编辑结构，场景 GLB 提供独立控制节点。新人物的独立 `.blend` / GLB 包含骨骼蒙皮与五段可导出的动画；碰撞仍采用平面范围和高度函数。昼夜、天气和远景群岛已接入。天空使用实时着色、星空与云层；云海使用保留透明度的积云贴图实例，没有使用体积光线追踪。远岛目前不可前往，天气尚不改变作物生长。角色表情、独立手指控制、布料物理、足部 IK、房屋室内、完整物理、音效、多人与云存档尚未实现。

网页模型通过 glTF Validator：0 错误、0 警告；实际自动化与浏览器检查详见 `reports/living_acceptance.md`。帧率只代表本机当时的运行表现。
