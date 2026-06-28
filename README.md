# Codex Game Skills

English | [简体中文](./README.zh-CN.md)

This repository is my personal exploration space for building up game-related Codex skills.

Each skill is self-contained. Skill-specific workflow details, requirements, behaviors, demos, and references should be read inside that skill directory.

## Skills

| Name | Description | Path |
| --- | --- | --- |
| `game-tileset-generator` | Turn user intent into atlas-based game tilesets through a production spec, layout-guided image generation, and deterministic postprocess stages. | `./game-tileset-generator` |

## Install

List installable skills:

```bash
./install-skill list
```

Install one skill:

```bash
./install-skill game-tileset-generator
```

By default, the installer copies the whole skill directory into your Codex skills directory.

Install one skill as a symlink:

```bash
./install-skill --symlink game-tileset-generator
```

Install all detected skills:

```bash
./install-skill --all
```

Install all detected skills as symlinks:

```bash
./install-skill --all --symlink
```

If an installation already exists, the installer replaces it automatically.
Restart Codex after installing new skills.
