# Codex Game Skills

English | [简体中文](./README.zh-CN.md)

This repository shares a series of skills I created while experimenting with game development using Codex.

## Skills

| Name | Path |
| --- | --- |
| `game-tileset-generator` | [./game-tileset-generator](./game-tileset-generator/) |

### `game-tileset-generator`

- Helps you refine and clarify your asset requirements.
- Outputs game tilesets ready to import into tools like Tiled.
- Reduces the manual cleanup and rework after GPT image generation.

When to use it:
- You have spent a long time looking for the right tileset.
- You need tilesets but cannot draw them yourself.

How to use it:
- Describe the game asset you want.
- The skill proposes a spec for you.
- Review it and confirm.
- The skill generates the final tileset.

What you get:
- `tileset_spec.json`: the approved spec
- `references/layout-guide.png`: the generated layout guide
- `final/atlas.png`: the final usable atlas

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
