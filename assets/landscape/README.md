# 坡地、河岸与粉色花树

从上轮可编辑的 `assets/layout/island_layout.blend` 继续制作，使用本地 Blender 5.2.1。上轮源文件、模型和预览完整保留，未调用 Tripo 或生成新的人物。

## 本轮变化

- 地表加入后方山坡、住宅缓坡、右侧低丘和前景微起伏；中央休闲区仍保持开阔。地形高度参数写入 `scene.json`，Blender 与网页采用一致采样，人物和路径随地面高度更新。
- 溪流沿原有弯道从上游约 13.755 米下降到下游 10.055 米，保留横向河湾和右下石桥。补充岸边苔藓、浅水石、芦草、零散水纹与上游岩石。
- 岛缘改为不规则轮廓，岩壁由大小不同的岩块、错落下垂的碎岩和垂藤组成；岛缘碎石、苔藓和花草连接草地与岩壁。
- 树木由 11 棵增加到 26 棵。新增 14 棵不同大小的绿树，主要位于后坡、两侧和岛缘；原来的粉色花树从 `assets/source/tree_blossom.blend` 恢复，位于住宅右侧、溪流左岸，树下有零散落花。
- 瀑布加入连贯水帘、不同长度的细流和水雾渐隐。原有动态水纹、昼夜、天气和自主生活继续运行。

## 文件与复现

`island_landscape.blend` 保留可编辑物件；`island_landscape.glb` 为网页合批版本；`scene.json` 包含高度、轮廓、树木与岩石碰撞、雨棚和日程位置。粉色树另保留命名节点，之后可以单独调整。

网页模型为 569,491 三角面、23,895,408 字节、20 个独立控制节点。前一版布局未被覆盖。人物继续使用已有 Tripo 骨骼资产。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/refine_landscape.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/render_layout.py -- --landscape
node scripts/test_layout.mjs landscape
node scripts/test_landscape.mjs
# gltf-validator 必须可解析，或通过 GLTF_VALIDATOR_MODULE 指定路径
node scripts/validate_landscape.cjs
```

旧存档沿用相同布局坐标和存储键；若保存位置落在新增树木上，加载时移到最近安全位置，作物、金币、库存和订单不清空。源文件中的原人物是占位，网页与预览渲染载入已有精细人物。

这一版继续改善场景层次，尚未达到参考图的所有细节。岩块仍偏风格化，瀑布采用水帘、流动着色和粒子，并非流体模拟；上游是缓坡溪流。坐姿、喝咖啡、室内和离线自主生活没有在本轮添加。
