# Codex Game Skills

[English](./README.md) | 简体中文

这个仓库是我个人用来探索和沉淀游戏相关 Codex Skills 的地方。

每个 skill 都是自包含的。具体到某个 skill 的 workflow、环境要求、行为说明、demo 和参考资料，应该进入对应 skill 目录查看。

## Skills

| Name | Description | 路径 | Demo |
| --- | --- | --- | --- |
| `game-tileset-generator` | Turn user intent into atlas-based game tilesets through a production spec, layout-guided image generation, and deterministic postprocess stages. | `./game-tileset-generator` | [Farm Soil](./game-tileset-generator/demo/stardew-farm-soil-64/run/final/atlas.png), [Farm Debris](./game-tileset-generator/demo/stardew-farm-debris-64/run/final/atlas.png) |

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
