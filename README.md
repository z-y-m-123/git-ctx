<div align="center">

**[English](#english) · [中文](#中文)**

</div>

---

<a id="english"></a>

# git-ctx

> Git, but for your AI context rules.

You tweak `.cursorrules` or `CLAUDE.md` to make the AI code better. Two hours later, the AI is generating garbage and you can't remember what you changed. Or your teammate asks "what rules are you using?" and you have to paste a blob of JSON into Slack.

`git-ctx` fixes this: one command to **snapshot**, **compare**, and **roll back** your AI context file — without mixing into Git history.

```
git-ctx init
# edit .ai-rules.json ...
git-ctx commit -m "added strict typing rules"
# AI output got worse?
git-ctx checkout -f 1
# back to what worked. done.
```



## Installation

### pip (recommended)

```bash
pip install git+https://github.com/z-y-m-123/git-ctx.git
# or, from a local clone:
pip install .
```

After install, the `git-ctx` command is available globally.

### install.sh (no pip needed)

```bash
curl -fsSL https://raw.githubusercontent.com/z-y-m-123/git-ctx/main/install.sh | bash
```

This downloads `git_ctx.py` from GitHub and installs it as `git-ctx`. If you run `./install.sh` from a local clone, it uses the local `git_ctx.py` instead. The installer prefers `/usr/local/bin` when writable, otherwise it uses `~/.local/bin`.

Optional environment overrides:

```bash
GIT_CTX_INSTALL_DIR="$HOME/bin" bash install.sh
GIT_CTX_REF="v0.2.0" bash install.sh
GIT_CTX_SOURCE_URL="https://example.com/git_ctx.py" bash install.sh
```

### Manual

```bash
cp git_ctx.py /usr/local/bin/git-ctx
chmod +x /usr/local/bin/git-ctx
```

**Requirements:** Python 3.8+ (standard library only — no dependencies).

## Quick Start

```bash
# Initialize in any project directory
git-ctx init
git-ctx init --template web-backend
git-ctx init --auto

vim .ai-rules.json

git-ctx status
git-ctx diff

git-ctx commit -m "add Python + FastAPI stack"

git-ctx log

git-ctx diff 1 2

git-ctx checkout -f 1
```

## Sharing With Git

For personal experiments, add `.ai-rules.json` and `.git-ctx/` to your project's `.gitignore`.

For team-shared context history, commit both `.ai-rules.json` and `.git-ctx/` to Git. Teammates can then inspect the shared history with `git-ctx log`, restore known-good versions with `git-ctx checkout`, and use `git-ctx branch` for context experiments.

## Commands

| Command | Description |
|---|---|
| `git-ctx init` | Create `.git-ctx/` and a default `.ai-rules.json` |
| `git-ctx status` | Show whether working rules differ from HEAD |
| `git-ctx diff [v1] [v2]` | Diff working rules vs HEAD, vs a specific version, or between two versions |
| `git-ctx commit -m <msg>` | Snapshot the current `.ai-rules.json` |
| `git-ctx log` | List all versions with timestamps and messages |
| `git-ctx show <version\|tag>` | Display the content of a version |
| `git-ctx checkout <id\|tag> [-f]` | Restore a version (prompts for confirmation unless `-f`) |
| `git-ctx tag` | Manage version tags (add, list, delete) |
| `git-ctx star <version\|tag>` | Star (bookmark) a version |
| `git-ctx unstar <version\|tag>` | Remove a star |
| `git-ctx stars` | List starred versions |
| `git-ctx branch [name]` | List branches or create a new one |
| `git-ctx switch <branch> [-f]` | Switch to a different context branch |
| `git-ctx merge <branch> [-f]` | Merge another branch into current |
| `git-ctx delete <version> [-f]` | Delete a version |
| `git-ctx validate` | Validate `.ai-rules.json` for completeness |
| `git-ctx export` | Export rules to AI tool formats (cursor, windsurf, claude, copilot) |
| `git-ctx wizard` | Interactive setup wizard to build `.ai-rules.json` |

### `init`

```bash
git-ctx init                         # default template
git-ctx init --template web-backend  # use a built-in template
git-ctx init --auto                  # auto-detect project type
```

Creates `.git-ctx/` directory and a default `.ai-rules.json` with an initial commit. Safe to run repeatedly (idempotent).

Built-in templates: `web-backend`, `web-frontend`, `cli-tool`, `library`, `data-science`, `minimal`.

### `status`

```bash
git-ctx status
```

Compares the working `.ai-rules.json` against the current version. Shows which branch you're on. Prints a hint when modified.

### `diff`

```bash
git-ctx diff              # working file vs HEAD
git-ctx diff 1            # working file vs version 1
git-ctx diff 1 2          # version 1 vs version 2
git-ctx diff v1-stable production  # using tag names
```

Uses unified diff format — the same format as `git diff`.

### `commit`

```bash
git-ctx commit -m "describe what changed"
```

Copies `.ai-rules.json` into `.git-ctx/<id>.json` and records the snapshot in `.git-ctx/index.json`. Refuses to commit if nothing changed since the current version.

### `log`

```bash
git-ctx log                # all versions
git-ctx log -n 5           # last 5 versions
git-ctx log -b main        # only versions on the 'main' branch
```

Prints version id, timestamp, commit message, branch, tags, and star markers for every snapshot.

### `show`

```bash
git-ctx show 3             # display version 3 as Markdown
git-ctx show production    # display the version tagged 'production'
git-ctx show 3 --json      # display raw JSON
```

View a version's content without checking it out.

### `checkout`

```bash
git-ctx checkout 3         # prompts for confirmation
git-ctx checkout -t prod   # by tag name
git-ctx checkout -f 3      # force: skip confirmation
```

Overwrites `.ai-rules.json` with the chosen version. **Always creates a timestamped backup** in `.git-ctx/backup-*.json` before overwriting.

### `tag`

```bash
git-ctx tag add 3 production    # tag version 3 as 'production'
git-ctx tag list                # list all tags
git-ctx tag delete production   # remove a tag
```

Tags work anywhere a version ID is accepted: `checkout`, `show`, `diff`, `star`, `delete`.

### `star` / `unstar` / `stars`

```bash
git-ctx star 3                  # bookmark version 3
git-ctx star production         # bookmark by tag name
git-ctx unstar 3                # remove bookmark
git-ctx stars                   # list all starred versions
```

Starred versions show a `[*]` marker in `git-ctx log`. Use stars to mark production-ready configs, best-performing prompts, or team-recommended versions.

### `branch` / `switch` / `merge`

```bash
git-ctx branch                  # list branches (* = current)
git-ctx branch experiment       # create a new branch at current version
git-ctx switch experiment       # switch to 'experiment' branch
git-ctx switch experiment -f    # skip uncommitted changes warning
git-ctx merge experiment        # merge 'experiment' into current branch
git-ctx merge experiment -f     # skip confirmation prompt
```

Context branches let you experiment with different rule sets without affecting the main line. Merge shows a diff before confirming.

### `delete`

```bash
git-ctx delete 4 -f     # force-delete version 4
```

Removes a version, its snapshot file, and cleans up associated tags, stars, and branch pointers. Refuses to delete the only remaining version.

### `validate`

```bash
git-ctx validate
```

Checks `.ai-rules.json` for missing recommended fields, empty tech stack, default project name, and type errors. Returns non-zero exit code on errors (useful for CI).

### `export`

```bash
git-ctx export                        # export to all formats
git-ctx export -f claude              # export to CLAUDE.md only
git-ctx export -f cursor --stdout     # print .cursorrules to stdout
git-ctx export --version 3 -f claude  # export a specific version
```

Converts `.ai-rules.json` to Markdown for different AI tools:
- `cursor` -> `.cursorrules`
- `windsurf` -> `.windsurfrules`
- `claude` -> `CLAUDE.md`
- `copilot` -> `.github/copilot-instructions.md`

### `wizard`

```bash
git-ctx wizard
```

Interactive Q&A session that guides you through building a `.ai-rules.json` step by step. Great for newcomers.

## How It Works

```
your-project/
├── .ai-rules.json          <- the working file (you edit this)
└── .git-ctx/               <- the repository (git-ctx manages this)
    ├── index.json           <- version metadata + branches + tags + stars
    ├── 1.json               <- snapshot of version 1
    ├── 2.json               <- snapshot of version 2
    └── backup-*.json         <- auto-backups from checkout/switch
```

- Every `commit` copies `.ai-rules.json` -> `.git-ctx/<id>.json` and appends to `index.json`.
- `diff` / `checkout` read snapshots from `.git-ctx/` and compare or restore them.
- `checkout` and `switch` always back up the current file before overwriting.
- Branches track independent lines of context changes, each with their own HEAD pointer.
- Tags and stars are stored in `index.json` as lightweight references.

## The `.ai-rules.json` Format

The default template:

```json
{
  "project": "my-project",
  "techStack": [],
  "codingStandards": [],
  "architectureDecisions": []
}
```

You can add **any fields you want** — git-ctx happily snapshots arbitrary JSON. Common additions: `"testingStrategy"`, `"apiConventions"`, `"deployNotes"`, or free-form prompts for your AI tool.

Check out [`examples/.ai-rules.json`](examples/.ai-rules.json) for a realistic example.

## Use With Other AI Context Files

`git-ctx` doesn't care about the filename — just symlink or rename your context file:

```bash
# If your AI tool reads .cursorrules instead:
ln -sf .ai-rules.json .cursorrules

# Or use the export command:
git-ctx export -f cursor
```

## FAQ

**Can I track files other than `.ai-rules.json`?**
Not yet — the filename is currently fixed. Symlink as a workaround. Custom filename support is planned.

**Does this replace Git?**
No. `git-ctx` only tracks `.ai-rules.json`. Use Git for your actual source code. Add `.git-ctx/` and `.ai-rules.json` to your `.gitignore` if you don't want them in version control.

**Can my team share the context history?**
Yes — commit the `.git-ctx/` directory to Git and teammates can `git-ctx log` / `git-ctx checkout` from the shared history. Use branches for parallel experimentation and merge to integrate changes.

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center"><b><a href="#中文">中文文档</a></b></p>

---

<a id="中文"></a>

# git-ctx

> Git，但是给 AI 上下文规则用的。

你反复调整 `.cursorrules` 或 `CLAUDE.md` 来让 AI 写出更好的代码。两小时后 AI 开始胡言乱语，你却忘了改过什么。或者同事问你「你用的什么规则配置？」你只能把一坨 JSON 粘贴到微信里。

`git-ctx` 解决的就是这个：**一条命令快照、对比、回滚**你的 AI 上下文文件，不污染项目 Git 历史。

```
git-ctx init
# 编辑 .ai-rules.json ...
git-ctx commit -m "加上严格类型检查规则"
# AI 输出变差了？
git-ctx checkout -f 1
# 回滚到好用的版本，搞定。
```



## 安装

### pip（推荐）

```bash
pip install git+https://github.com/z-y-m-123/git-ctx.git
# 或者本地克隆后安装：
pip install .
```

安装后 `git-ctx` 命令全局可用。

### install.sh（免 pip）

```bash
curl -fsSL https://raw.githubusercontent.com/z-y-m-123/git-ctx/main/install.sh | bash
```

脚本会将 `git_ctx.py` 复制到 `~/.local/bin/git-ctx`。请确保 `~/.local/bin` 在 `$PATH` 中。

### 手动安装

```bash
cp git_ctx.py /usr/local/bin/git-ctx
chmod +x /usr/local/bin/git-ctx
```

**环境要求：** Python 3.8+（仅依赖标准库，零第三方依赖）。

## 快速开始

```bash
# 在任意项目目录初始化
git-ctx init
git-ctx init --template web-backend
git-ctx init --auto

vim .ai-rules.json

git-ctx status
git-ctx diff

git-ctx commit -m "添加 Python + FastAPI 技术栈"

git-ctx log

git-ctx diff 1 2

git-ctx checkout -f 1
```

## 命令参考

| 命令 | 说明 |
|---|---|
| `git-ctx init` | 创建 `.git-ctx/` 和默认 `.ai-rules.json` |
| `git-ctx status` | 显示工作区规则是否与 HEAD 有差异 |
| `git-ctx diff [v1] [v2]` | 对比工作区 vs HEAD，或对比两个指定版本 |
| `git-ctx commit -m <msg>` | 将当前 `.ai-rules.json` 保存为快照 |
| `git-ctx log` | 列出所有版本及其时间戳和提交信息 |
| `git-ctx show <version\|tag>` | 查看某个版本的内容 |
| `git-ctx checkout <id\|tag> [-f]` | 恢复某个版本（默认需确认，`-f` 跳过） |
| `git-ctx tag` | 管理版本标签（add、list、delete） |
| `git-ctx star <version\|tag>` | 收藏（书签）一个版本 |
| `git-ctx unstar <version\|tag>` | 取消收藏 |
| `git-ctx stars` | 列出所有收藏的版本 |
| `git-ctx branch [name]` | 列出分支或创建新分支 |
| `git-ctx switch <branch> [-f]` | 切换到另一个 Context 分支 |
| `git-ctx merge <branch> [-f]` | 合并分支到当前分支 |
| `git-ctx delete <version> [-f]` | 删除一个版本 |
| `git-ctx validate` | 验证 `.ai-rules.json` 的完整性和一致性 |
| `git-ctx export` | 导出规则到各 AI 工具格式 |
| `git-ctx wizard` | 交互式向导，逐步构建 `.ai-rules.json` |

### `init`

```bash
git-ctx init                         # 默认模板
git-ctx init --template web-backend  # 使用内置模板
git-ctx init --auto                  # 自动检测项目类型
```

创建 `.git-ctx/` 目录和默认 `.ai-rules.json`，并自动生成初始提交。可重复执行（幂等）。

内置模板：`web-backend`、`web-frontend`、`cli-tool`、`library`、`data-science`、`minimal`。

### `status`

```bash
git-ctx status
```

对比工作区 `.ai-rules.json` 与当前版本。显示当前分支。干净时打印匹配信息，有修改时给出提示。

### `diff`

```bash
git-ctx diff              # 工作区 vs HEAD
git-ctx diff 1            # 工作区 vs 版本 1
git-ctx diff 1 2          # 版本 1 vs 版本 2
git-ctx diff v1-stable production  # 使用标签名
```

使用 unified diff 格式 —— 和 `git diff` 一样的输出风格。

### `commit`

```bash
git-ctx commit -m "描述本次改动"
```

将 `.ai-rules.json` 复制到 `.git-ctx/<id>.json` 并在 `.git-ctx/index.json` 中记录快照。如果工作区与当前版本一致，则拒绝提交。

### `log`

```bash
git-ctx log                # 所有版本
git-ctx log -n 5           # 最近 5 个版本
git-ctx log -b main        # 仅显示 main 分支的版本
```

按时间顺序打印每个版本的 id、时间戳、提交信息、分支、标签和收藏标记。

### `show`

```bash
git-ctx show 3             # 以 Markdown 格式显示版本 3
git-ctx show production    # 显示标签为 'production' 的版本
git-ctx show 3 --json      # 显示原始 JSON
```

无需 checkout 即可查看版本内容。

### `checkout`

```bash
git-ctx checkout 3         # 交互确认
git-ctx checkout -t prod   # 通过标签名恢复
git-ctx checkout -f 3      # 强制切换，跳过确认
```

用指定版本覆盖 `.ai-rules.json`。**覆盖前自动创建时间戳备份** 保存到 `.git-ctx/backup-*.json`。

### `tag`

```bash
git-ctx tag add 3 production    # 将版本 3 标记为 'production'
git-ctx tag list                # 列出所有标签
git-ctx tag delete production   # 删除标签
```

标签可用于任何接受版本 ID 的命令：`checkout`、`show`、`diff`、`star`、`delete`。

### `star` / `unstar` / `stars`

```bash
git-ctx star 3                  # 收藏版本 3
git-ctx star production         # 通过标签名收藏
git-ctx unstar 3                # 取消收藏
git-ctx stars                   # 列出所有收藏的版本
```

收藏的版本在 `git-ctx log` 中显示 `[*]` 标记。适用于标记生产环境配置、最佳提示词或团队推荐版本。

### `branch` / `switch` / `merge`

```bash
git-ctx branch                  # 列出分支（* = 当前）
git-ctx branch experiment       # 在当前版本处创建新分支
git-ctx switch experiment       # 切换到 'experiment' 分支
git-ctx switch experiment -f    # 跳过未提交更改的警告
git-ctx merge experiment        # 将 'experiment' 合并到当前分支
git-ctx merge experiment -f     # 跳过确认提示
```

Context 分支让你可以试验不同的规则集而不影响主线。合并前会显示 diff 供审查确认。

### `delete`

```bash
git-ctx delete 4 -f     # 强制删除版本 4
```

删除版本及其快照文件，并清理关联的标签、收藏和分支指针。不允许删除仅剩的唯一版本。

### `validate`

```bash
git-ctx validate
```

检查 `.ai-rules.json` 是否缺少推荐字段、技术栈是否为空、项目名是否为默认值、以及类型错误。有错误时返回非零退出码（可用于 CI）。

### `export`

```bash
git-ctx export                        # 导出到所有格式
git-ctx export -f claude              # 仅导出到 CLAUDE.md
git-ctx export -f cursor --stdout     # 打印 .cursorrules 到标准输出
git-ctx export --version 3 -f claude  # 导出特定版本
```

将 `.ai-rules.json` 转换为各 AI 工具的 Markdown 格式：
- `cursor` -> `.cursorrules`
- `windsurf` -> `.windsurfrules`
- `claude` -> `CLAUDE.md`
- `copilot` -> `.github/copilot-instructions.md`

### `wizard`

```bash
git-ctx wizard
```

交互式问答会话，逐步引导你构建 `.ai-rules.json`。非常适合新手。

## 工作原理

```
your-project/
├── .ai-rules.json          <- 工作文件（你编辑这个）
└── .git-ctx/               <- 仓库（git-ctx 自动管理）
    ├── index.json           <- 版本元数据 + 分支 + 标签 + 收藏
    ├── 1.json               <- 版本 1 的快照
    ├── 2.json               <- 版本 2 的快照
    └── backup-*.json         <- checkout/switch 时自动备份
```

- 每次 `commit` 将 `.ai-rules.json` -> `.git-ctx/<id>.json`，并追加到 `index.json`。
- `diff` / `checkout` 从 `.git-ctx/` 读取快照进行对比或恢复。
- `checkout` 和 `switch` 在覆盖前始终备份当前文件。
- 分支追踪独立的 Context 变更线，每个分支有自己的 HEAD 指针。
- 标签和星标存储在 `index.json` 中，作为轻量引用。

## `.ai-rules.json` 格式

默认模板：

```json
{
  "project": "my-project",
  "techStack": [],
  "codingStandards": [],
  "architectureDecisions": []
}
```

你可以 **随意添加任何字段** —— git-ctx 对任意 JSON 结构都能正常快照。常见的扩展包括：`"testingStrategy"`、`"apiConventions"`、`"deployNotes"`，或者直接写给 AI 工具的自由格式提示。

参考 [`examples/.ai-rules.json`](examples/.ai-rules.json) 查看真实场景示例。

## 配合其他 AI 上下文文件使用

`git-ctx` 不关心文件名 —— 用符号链接或导出即可：

```bash
# 如果你的 AI 工具读取 .cursorrules：
ln -sf .ai-rules.json .cursorrules

# 或使用 export 命令：
git-ctx export -f cursor
```

## 常见问题

**能追踪 `.ai-rules.json` 以外的文件吗？**
暂不支持 —— 文件名目前是固定的。可以用符号链接作为变通方案。自定义文件名功能已在规划中。

**这能替代 Git 吗？**
不能。`git-ctx` 只追踪 `.ai-rules.json`。源代码请继续用 Git 管理。如果不想把 `.git-ctx/` 和 `.ai-rules.json` 提交到 Git，可以将其加入 `.gitignore`。

**团队能共享上下文历史吗？**
可以 —— 将 `.git-ctx/` 目录提交到 Git，团队成员即可通过 `git-ctx log` / `git-ctx checkout` 查看和使用共享的历史记录。使用分支进行并行实验，通过 merge 整合变更。

## 许可证

MIT —— 详见 [LICENSE](LICENSE)。

---

<p align="center"><b><a href="#english">English Documentation</a></b></p>

---

<div align="center">

[Back to top / 回到顶部](#)

[English](#english) · [中文](#中文)

</div>
