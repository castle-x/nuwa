# 维护规则

这个仓库是一组 skill，内容是给 agent 读的操作方法。改动它的人（包括 agent）按下面的规则来。

## 结构

- `skills/<name>/SKILL.md`：每个 skill 的入口，frontmatter 里的 `description` 决定 agent 什么时候调用它。改 description 要想清楚会不会和其他 skill 抢触发。
- `skills/<name>/references/`：入口里按需链接的细节，入口只放判断和流程。
- `skills/<name>/scripts/`：可直接运行的脚本。
- 分两层：造人（`nuwa` 及 casting、body、wardrobe）产出角色包；做内容（`nuwa-studio` 及公共环节 set、motion、polish 和各内容形式分支，含静帧的 `nuwa-aesthetic`）使用角色包。
- 每个子 skill 只写本环节特有的东西；跨环节的规则写在 `skills/nuwa/`，视频通用规则写在 `skills/nuwa-motion/`，子 skill 链接过去，不要复制。
- `research/`：维护用的实测记录，只留在维护者本地，已写进 `.gitignore`，不进公开仓库。没有这个目录时，实测过程写在 Issue 或 PR 描述里。

## 交付版的要求

`skills/` 下的内容会直接交付给使用者，必须做到：

- **自包含。** 不依赖、不引用任何外部 skill。需要的方法写进本集合。
- **只写结论。** 不写日期、人名、"实测""复盘""用户评价"这类过程记录，也不写内部待办。
- **注明适用模型。** 提示词示例和写法要写清针对哪个模型，因为提示词不通用。
- **示例可以保留原文**，但只写"复用时注意什么"，不写"那次结果怎样"。

模板里给使用者填写的字段（比如档案里的"用户确认：<日期>"）不算过程记录，可以保留。

## 两条铁律

**数字给人看，比例和形态给模型。** 身高、三围、尺码这类测量数字模型执行不了，设定都分"给人看的参数"和"给模型执行的描述"两层，提示词里只放后者。

**流程通用，提示词不通用。** 
工作流程（环节、参考分工、留档、验收）是通用的；具体的提示词和写法只在特定模型上成立。模型的长处、短处和写法集中维护在 `skills/nuwa/references/model-capabilities.md`，子 skill 引用它，不各自另写一份。

## 自进化：从实测到交付

1. 每次生成后，把模型、通道、参数、写法、结果、用户评价记进 `research/experiment-log.md` 对应主题下。
2. 结论被反复验证，或新旧冲突经横测有了结果，更新 `research/model-evidence.md`。
3. 把稳定的结论提炼成不带日期和来源的规则，写进 `skills/` 对应的文件。被推翻的旧规则直接改掉，不要让两条矛盾的规则同时留在交付版里。
4. 用户认可的提示词逐字保存，不要凭记忆重写。

提炼后写到哪：

| 内容 | 位置 |
|---|---|
| 模型能力、参数、有效和翻车的写法 | `skills/nuwa/references/model-capabilities.md` |
| 参考图怎么分工 | `skills/nuwa/references/reference-roles.md` |
| 服装合成示例 | `skills/nuwa-wardrobe/references/examples.md` |
| 场景配方 | `skills/nuwa-set/references/scene-recipes.md` |
| 视觉美学方法、概念写真示例 | `skills/nuwa-aesthetic/`（示例写进 `references/examples.md`） |
| 视频生成通用规则 | `skills/nuwa-motion/` |
| 某种内容形式的写法和示例 | 对应的形式分支，比如 `skills/nuwa-dance/` |
| 新的内容形式 | 新建一个 `skills/nuwa-<形式>/`，并在 `nuwa-studio` 的形式表里登记 |
| 问题和修法 | `skills/nuwa-polish/references/failure-atlas.md` |

## 吸收外部 skill 时

把外部 skill 的方法改写进本集合时，先把它的入口文件和每一份参考文件都读完，逐条对照哪些写进来了、哪些没有，再改写。只读入口文件会漏掉放在细则里的关键经验。

## 不要放进仓库的东西

- 密钥、接口地址里的签名、账号信息。
- 具体项目的文件路径和批次记录（那些属于项目自己的制作档案）。
- 真人照片和生成的成片。示例只存提示词原文和文字描述。

## 语言

正文用中文。提示词保持提交时的原文。
