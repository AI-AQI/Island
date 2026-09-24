# 围绕中央草地重新组织的小岛

本版根据主视角参考图重做空间关系，读取原有 `island_dusk_living.blend`，用本地 Blender 生成。前面的精修版、动态版和扩建版均保留，未调用 Tripo 或重新生成角色。

住宅在左上、菜田与羊圈在左侧下方、咖啡馆在右上，桥移到右下。中央由相连草地、石径、小广场和长椅构成；建筑保留原尺寸，不随地形放大。重新布置河岸石块、花丛、灌木、大小树冠和岛缘植被。

溪流有 193 个曲线采样点，从偏左上入口绕向右侧，再在桥的上游横向转弯，向右下瀑布出口展开。水面宽度从约 1.6 米增加到 6.8 米。水流纹理沿曲线前进，桥按河道朝向旋转。地形、碰撞、寻路、雨棚、作物入口和日程地点一并更新。

当前场景地形半径为 28 × 21.5 米。新的河道采用二维曲线距离采样，不再要求任意横截面只能有一条竖向河流。运行时使用同一组曲线数据。地形不规则边缘和岸边装饰仍采用简化碰撞，这不是完整物理模拟。

## 文件

- `island_layout.blend`：独立物件的可编辑源文件；原人物占位保留，网页另载入已有 Tripo 角色。
- `island_layout.glb`：500,151 三角面、20,600,572 字节，静态场景合批，19 个动态控制节点保留。
- `scene.json`：河道、地形、桥朝向、碰撞、生活地点、灯光与瀑布发射位置。
- `../../scripts/layout_spec.py`、`recompose_island.py`：固定随机种子的构建脚本。
- `../../scripts/render_layout.py`：从最终源文件渲染主视角与俯视图，预览时加入现有人物。
- `../../renders/layout/comparison.html`：原参考、主视角预览与俯视布局。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/recompose_island.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/render_layout.py
node scripts/test_layout.mjs
# 需要 gltf-validator，或通过 GLTF_VALIDATOR_MODULE 指定其路径
node scripts/validate_layout.cjs
```

旧存档位置投射到最近可行走位置，并记录布局版本 3；作物、计时、库存、金币和订单不清空。自主生活、昼夜天气、远景群岛继续使用已有系统。此轮重点是构图和空间组织；岩体自然度、上游山地层次、植被与建筑细部仍与参考有差距。离线预览使用原黄昏天空，网页继续使用动态天空与远岛。
