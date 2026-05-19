# ForMyDJ as a universal AI skill

ForMyDJ ships as a plain CLI (`formydj`) plus skill manifests for the major AI agent platforms. Once the CLI is installed, any agent (Claude, Codex, Gemini, ChatGPT with shell access, Cursor, etc.) can invoke it directly.

## One-line install (any agent can run this)

```bash
pip install "git+https://github.com/sloppamadewithlove/ForMyDJs.git"
```

You still need `ffmpeg` and `yt-dlp` as system tools:

| OS      | Command                                                |
|---------|--------------------------------------------------------|
| macOS   | `brew install ffmpeg yt-dlp`                           |
| Linux   | `sudo apt-get install ffmpeg && pip install yt-dlp`    |
| Windows | `scoop install ffmpeg yt-dlp`                          |

Verify:

```bash
formydj version          # prints 0.2.0
formydj check-update     # confirms it can reach GitHub
```

## Platform-specific skill manifests

Each agent has its own skill format. Pick the one you use and install the matching file:

### Claude Code

Copy `claude/SKILL.md` to `~/.claude/skills/formydj/SKILL.md`:

```bash
mkdir -p ~/.claude/skills/formydj
cp skills/claude/SKILL.md ~/.claude/skills/formydj/SKILL.md
```

Claude will auto-discover it on the next session.

### Codex / generic shell-using agents

Codex looks for `AGENTS.md` files in the working directory. Either:

- Drop `codex/AGENTS.md` into the root of your project, or
- Symlink to it: `ln -s "$(pwd)/skills/codex/AGENTS.md" ~/AGENTS.md`

### Gemini CLI

```bash
mkdir -p ~/.gemini/skills/formydj
cp skills/gemini/skill.toml ~/.gemini/skills/formydj/skill.toml
```

### Anything else (Cursor, Cline, Aider, custom agents)

Point the agent at this directory and tell it:

> ForMyDJ is a local CLI tool. Run `formydj --help` for usage. It downloads
> and converts SoundCloud/YouTube links and local audio files for DJ use.

Any reasonable agent can take it from there.

## Why this exists

Most "download a track" workflows route the user through sketchy ad-funded converter websites. ForMyDJ keeps the whole pipeline local: your AI assistant calls the CLI on your machine, the CLI calls `yt-dlp` and `ffmpeg`, and the file lands in your DJ folder. No third party sees your library, your queue, or your DJ name.

## Updating

```bash
formydj check-update           # prints latest version + release URL
pip install -U "git+https://github.com/sloppamadewithlove/ForMyDJs.git"
```

The macOS app surfaces an in-window banner when an update is available.
