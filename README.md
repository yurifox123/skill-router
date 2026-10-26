<!-- SEO: AI Skill repository, Codex skill management, Agent Skills, context optimization, token efficiency -->

# Skill Router：构建轻量的 AI Skill 仓库，减少上下文占用

> **English summary:** Skill Router is a lightweight AI Agent Skill repository and routing layer. It keeps inactive skills outside automatic discovery, maintains a searchable registry, and loads only the skills required for the current task to reduce context overhead and token cost.

codex安装了越来越多的 skills，能力会变强，但上下文也会变得越来越臃肿。每个项目都加载一大批平时用不到的 skill，会带来更高的固定开销、更长的技能列表和更低的任务聚焦度。

**Skill Router** 用一个轻量的路由 skill 管理 Skill 仓库，让 Agent 只在真正需要时取用对应能力。

它的目标很简单：

> 让运行环境保持轻量，让任务按需取用 skill，让不相关的 skill 不进入当前上下文。

## Skill 仓库解决什么问题？

传统的 skill 使用方式通常是把所有 skill 放在自动扫描目录中：

```text
~/.codex/skills/
├── documents/
├── graphify/
├── playwright-skill/
├── presentations/
├── spreadsheets/
├── ui-ux-pro-max/
└── ...
```

当 skill 数量增加后，会出现几个问题：

- 不相关的 skill 也进入全局 skill 清单
- 每个项目都背负相同的 skill 目录开销
- skill 描述和工具说明占用上下文
- Agent 更容易被相似或无关能力干扰
- 很难知道某个项目到底启用了哪些 skill
- 禁用 skill 后，之后重新启用不方便

Skill Router 将“技能仓库”和“当前使用”分开：

```text
技能仓库：保存全部 skill，但不自动加载
索引目录：保存技能的短信息和状态
使用目录：只放当前任务确认需要的 skill
```

## 核心设计：技能仓库不参与自动发现

Skill Router 使用一个普通目录保存未启用的 skill：

```text
~/.codex/skill-library/
├── packages/
│   ├── graphify/
│   ├── playwright-skill/
│   ├── documents/
│   └── ...
├── registry.jsonl
└── registry.md
```

`skill-library` 是 Skill Router 的自定义存储目录，不是 Codex 的原生 skill 机制。Codex 不会自动扫描这里的完整 `SKILL.md`。

只有用户明确取用 skill 后，Skill Router 才会把它复制到当前 Agent 能发现的使用位置。仓库始终保留完整源包，未取用的 skill 不会进入当前任务的上下文。

Skill Router 的简介只挂出索引链接，不读取索引正文：`references/registry-schema.md` 用于修复格式，`skill-library/registry.jsonl` 是 Agent 查询用的清单，`skill-library/registry.md` 是可读清单。只有 Router 被使用时，才按当前任务读取其中需要的文件或条目。

## 可读的 Skill 仓库清单

Skill Router 维护两个清单文件：

```text
registry.jsonl   # 给脚本和 Agent 使用
registry.md      # 给人查看
```

`registry.md` 是仓库的可读目录，会列出：

- skill 名称
- 功能说明
- 标签
- 依赖关系
- Token 估算
- 技能来源
- 技能存储路径

路由器会在索引更新时自动创建或重新生成 `registry.md`，不需要手动维护这份可读清单。

技能简介集中放在仓库索引中，不写进每个项目的固定上下文。平时项目只保留轻量的 Skill Router；只有真正使用路由器时，才按任务读取相关索引并产生额外上下文。索引由 Router 自动生成和同步，不应手动编辑。

## 安装和使用

将这个仓库作为一个 Agent Skill 安装后，直接告诉 AI 你想管理什么：初始化技能仓库、查看技能清单、为当前任务推荐技能、取用某个 skill，或归档并恢复已使用的 skill。Skill Router 会先读取短索引，再在确认后处理完整 skill 包。

完整技能存放在仓库中，未被取用的技能不会进入自动扫描目录，因此不会持续占用当前任务的上下文。

## Skill 仓库工作流程

```mermaid
flowchart LR
    A[收集 skill] --> B[存入仓库]
    B --> C[生成短索引]
    C --> D[检索和推荐]
    D --> E[用户确认取用]
    E --> F[复制完整 skill]
    F --> G[任务完成后归档或恢复]
```

典型流程如下：

1. 将完整 skill 包存入仓库，保留 `SKILL.md`、references、scripts 和 assets；全局 `~/.codex/skills/` 只保留 `skill-router`，其他用户 skill 由 Router 移入 `skill-library/packages/`。
2. 从 frontmatter 生成短索引，记录功能、标签、依赖、大小和 Token 估算。
3. 只读取索引匹配用户需求，不扫描所有完整 skill。
4. 推荐少量候选 skill，并显示取用成本和依赖关系。
5. 用户确认后，复制对应的完整 skill 包到当前使用位置。
6. 使用完成后可以归档，之后通过索引再次取用；项目 skill 放在项目的 `.agents/skills/`，不会重新写入全局 skill 根目录。

推荐阶段只读取索引，不读取技能库中的全部 `SKILL.md`，从而避免为了推荐一个 skill 而加载整个技能库。

在项目场景中，路由器的主要产物是项目级 skill 集合：用户确认后，只把当前项目需要的 skill 放入项目的 `.agents/skills/`，其他 skill 继续留在仓库中。这样每个项目只携带自己的能力边界，项目切换时也不会把无关 skill 一起带入。

## 使用方法

直接告诉 AI 想做什么。

第一次使用时，可以这样说：

> 帮我初始化 Skill 仓库，把现有的 skills 收纳进去，并生成一份可读清单。

查看仓库内容时，可以说：

> 列出当前 Skill 仓库里的技能，并按功能分类。

为当前任务寻找能力时，可以说：

> 这个项目需要浏览器自动化、页面截图和 E2E 测试，请从 Skill 仓库推荐合适的技能，并说明各自的上下文成本。

确认取用时，可以说：

> 启用刚才推荐的浏览器测试技能，完成后告诉我哪些 skill 被取用了。

任务结束后，可以说：

> 归档这次任务用到的临时 skill，保留以后恢复的能力。

需要恢复时，可以说：

> 恢复上次归档的浏览器测试 skill。

如果仓库里没有合适能力，可以说：

> 仓库里没有合适的 skill，请告诉我缺少什么能力，以及是否值得创建一个新的 skill。

Skill Router 会先展示推荐和影响，再执行取用、归档或恢复，避免未经确认改变技能仓库。

## 仓库安全和可恢复性

Skill Router 默认把禁用的 skill 移到备份目录，而不是直接删除：

```text
~/.codex/skill-library/backups/
```

因此普通的归档操作可以通过恢复流程还原。只有明确执行永久清理时才会删除仓库中的备份。

启用已有目录时，Skill Router 默认拒绝覆盖，避免意外破坏项目配置。需要替换时必须显式使用 `--replace`。

平台管理的 `.system` skills、插件缓存和工具说明不属于用户自定义 skill，Skill Router 不会修改它们。

运行全局初始化后，用户管理的全局目录只保留 `skill-router`；其他全局 skill 会被移动到 `~/.codex/skill-library/packages/`，并同步重建 `registry.jsonl` 与 `registry.md`。`.system` 等平台目录按原样保留。

## 上下文开销对比（未激活口径）

拿我的codex举例

这里比较的是**没有读取 skill 正文**时的固定发现信息：skill 名称、简介和路径元数据。未激活的 skill 不会把完整 `SKILL.md` 放进上下文。

按我的仓库 43 个 skill 的 registry，使用 `cl100k_base` 统计：

| 方式 | 固定发现信息 | 说明 |
|---|---:|---|
| 全部 43 个 skill 出现在固定目录 | **约 3,867 tokens** | 只包含名称和简介；包含路径时约 4,269 tokens |
| 只有 Skill Router 出现在固定目录 | **约 51 tokens** | 只有 Router 的名称和简介及索引链接 |
| 固定开销减少 | **约 3,816 tokens** | 约减少 **98.7%**，约为原来的 **1/76** |

Skill Router 自身的完整正文约 **958 tokens**，只有实际使用路由器时才读取。此时它通过脚本查询索引，只返回与当前项目匹配的少量条目；不会把整个 `registry.md` 或所有 skill 正文读入上下文。

## 上下文优化效果

Skill Router 不能删除 Codex 平台本身的固定工具说明和系统规则，但可以让仓库中的大多数 skill 保持在非自动扫描状态：

| 模式 | Skill 仓库上下文 |
|---|---:|
| 所有 skill 放在自动扫描目录 | 高，随技能数量增长 |
| 完整 skill 保存在仓库 | 低，只读取短索引 |
| 用户确认后取用 | 只增加当前任务需要的技能 |

这种方式适合希望控制 Token 成本、减少上下文噪声、提高 Agent 专注度的开发者和团队。

## 适合谁？

Skill Router 适合：

- 使用 Codex 或其他支持 Agent Skills 的开发者
- 安装了很多 skills，但一次任务只需要其中一部分的人
- 关注上下文窗口和 Token 成本的团队
- 需要在多个项目之间切换不同工具链的人
- 希望把 skill 资产纳入统一管理和版本控制的人
- 正在实践上下文工程、按需加载和轻量化 Agent 的团队

## 设计原则

Skill Router 遵循四个原则：

1. **索引优先**：推荐时读取短索引，不扫描所有完整 skill。
2. **项目级取用**：确认后只把当前项目需要的 skill 放入项目级目录。
3. **仓库与使用分离**：完整 skill 继续留在仓库中，不进入无关项目上下文。
4. **操作可恢复**：禁用默认归档，保留恢复路径。

## 总结

Skill Router 是一个 Skill 仓库管理层。它把完整技能放在非自动扫描的仓库中，只将当前真正需要的能力取出使用。

通过技能索引、按需取用、仓库归档和可恢复操作，Skill Router 可以帮助 AI 编程环境减少上下文占用，降低 Token 开销，并让 Skill 资产保持轻量、清晰和可控。

如果你的skill 已经增长到几十个，Skill Router 可以作为一个简单的上下文优化器。
