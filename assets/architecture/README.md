# 建筑近景精修

在 `assets/landscape/island_landscape.blend` 上制作，只读上一版。采用本地 Blender 建模和程序纹理，没有使用新的外部生成任务。

- 住宅：细分拱窗格、弧形木框、侧边窗帘、石窗台、门扉五金、入口瓦檐、白粉攀爬花藤。保留建筑占地和总高度。
- 咖啡厅：木瓦色差收敛、屋脊降低约 0.33 米，新增后墙格窗、屋檐花藤、柜台木条。粉白伞改为曲面布伞，增加压边、伞骨、杯碟、杯把和餐巾。
- 建筑使用独立 512 像素程序纹理：木纹、灰泥、石材、瓦片与织物的颜色、粗糙度和切线空间法线。环境旧材质未替换。
- 四个建筑节点独立保留，不随环境合批一起减面。原有角色、水体、作物、羊、猫、小船和粉色树控制节点仍存在。

`island_architecture.blend` 是完整可编辑版；`island_architecture.glb` 是网页减面版。GLB 共 **682,207 三角面、38,352,204 字节、24 个独立控制节点**（环境合批节点另计）。与上一版 23.9 MB 相比加载量增加，已将网页版本限制在 70 万三角面、40 MB 内。纹理来源与前后建筑范围记录于 `scene.json`。

地形、河道、树木位置、桥、生活地点和雨棚范围与上一版一致。窗灯和木石材质沿用昼夜、雨天响应；现有存档无需迁移版本升级。

## 查看与重建

- 动态网页：`http://127.0.0.1:8765/viewer/`
- 近景及前后对照：`http://127.0.0.1:8765/renders/architecture/comparison.html`
- `scripts/crafted_architecture.py`：模型细部。
- `scripts/refine_architecture.py`：材质、替换、可编辑场景和网页减面导出。

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b -t 6 --python scripts/refine_architecture.py
/Applications/Blender.app/Contents/MacOS/Blender -b -t 6 --python scripts/render_layout.py -- --architecture
node scripts/test_layout.mjs architecture
GLTF_VALIDATOR_MODULE=/path/to/gltf-validator node scripts/validate_landscape.cjs architecture
```

离线预览使用完整模型、Cycles 和原黄昏背景，网页使用减面模型与实时灯光，效果存在差别。这是向参考图继续靠近的一轮素材精修，尚未达到逐像素一致；植被、岩体、水和小道的细部仍可继续完善。
