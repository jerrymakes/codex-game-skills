# Codex Game Skills

[English](./README.md) | 简体中文

这个仓库分享了我在尝试用 Codex 开发游戏时制作的一系列 skills。

## Skills

| Name | 路径 |
| --- | --- |
| `game-tileset-generator` | [./game-tileset-generator](./game-tileset-generator/) |

### `game-tileset-generator`

- 辅助你细化和明确素材生成需求
- 直出游戏瓦片图，可导入 Tiled 等游戏开发工具
- 降低 GPT 出图后大量手工整理和返工成本

适合什么场景：
- 找了很久找不到想要的瓦片图
- 不会画瓦片图

怎么用：
- 描述你想要的游戏素材
- skill 会生成建议
- 等你确认
- skill 会生成最终的瓦片图

会产出什么：
- `tileset_spec.json`：确认后的规格
- `references/layout-guide.png`：生成参考布局图
- `final/atlas.png`：最终可用图集 atlas

## 安装

先列出当前仓库里可安装的 skills：

```bash
./install-skill list
```

安装单个 skill：

```bash
./install-skill game-tileset-generator
```

默认会复制整个 skill 目录到 Codex 的 skills 目录中。

如果你希望用软链接安装单个 skill：

```bash
./install-skill --symlink game-tileset-generator
```

安装仓库里全部可检测到的 skills：

```bash
./install-skill --all
```

如果你希望把全部 skill 都安装成软链接：

```bash
./install-skill --all --symlink
```

如果已存在同名安装，安装脚本会自动替换。
安装新 skill 后，重启 Codex。
