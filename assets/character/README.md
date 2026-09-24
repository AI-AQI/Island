# 雏菊 · 本地 Blender 人物

按 `reference/character/original.png` 制作的第一版可动角色。模型、材质纹理、蒙皮、动作和浇水壶均由本机 Blender 5.2.1 生成，不使用 Tripo 或其他在线模型服务。

打开 [初版人物对照](http://127.0.0.1:8765/viewer/character.html?model=local) 可旋转查看全身、面部、背面，并切换五个动作、暂停和慢速播放。游戏主页目前使用后续制作的 [Tripo 精细版](../character_tripo/README.md)，本目录保留第一版资产。

## 文件

- `daisy_character.blend`：完整可编辑源文件，272,170 三角面，包含摄影棚、相机、灯光、打包材质、15 个模型部件与 `Daisy_Rig` 骨架。默认待机姿态；在 Dope Sheet 的 Action Editor 中选择动作。
- `daisy_character.glb`：131,121 三角面，11,017,912 字节；27 根骨骼、五段蒙皮动画、8 张内嵌材质图片。网页加载该文件，不需要联网下载依赖。
- `textures/`：本地生成的布料、草编和皮革底色/法线纹理。Blender 源文件中也已打包。
- `../../renders/character/`：完整模型的正面、背面、侧面、面部与动作检查渲染。网页模型经过减面，实时光照与离线渲染不同。

## 骨骼与动作

`root → pelvis → spine → chest → neck → head`；另有双臂、双腿、手、脚、帽子、三组头发、四组裙摆和挎包骨骼。使用归一化顶点蒙皮权重，手指几何随手骨移动。

| 动作 | 时长 | 用途 |
| --- | --- | --- |
| Idle | 3 秒 | 呼吸、轻微转头与配饰摆动 |
| Walk | 1.33 秒 | 原地循环步态，位移由游戏导航控制 |
| Plant | 2.17 秒 | 弯腰伸手播种 |
| Water | 3 秒 | 拿壶前倾浇水姿态 |
| Harvest | 2.33 秒 | 弯腰伸手收取 |

`Watering_Can` 绑定左手，网页只在 Water 动作期间显示；在 Blender 手动查看浇水动作时，需要开启该物件的渲染可见性。动作期间游戏暂时锁定移动和再次互动，结束后恢复待机；不改变原存档格式。

## 重现

在项目根目录执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python scripts/build_character.py -- --width 960 --samples 48 --export --details
GLTF_VALIDATOR_MODULE=/path/to/gltf-validator node scripts/validate_character.cjs
node scripts/test_living.mjs
```

脚本先保存完整源文件，再对导出副本减面、三角化，保留权重和动画，并修复少量退化 UV 角点的零切线。不要对这个文件运行原来的静态场景法线压缩器。

## 当前精度

这是依据单张参考图构建的风格化首版，并非像素级或影视级复刻。衣帽、发型和配饰已经落到可编辑几何，面部神态、发束衔接和布料褶皱仍有明显精修空间。尚未制作面部表情、眨眼、独立手指绑定、布料物理、足部 IK 或完整的工具握持动画；五段动作是游戏原型动作。背面细节按正面服装逻辑补全。
