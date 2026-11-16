# 参与贡献

欢迎提 Issue 和 Pull Request。Nuwa 的价值主要来自一次次真实生成里攒下的经验，所以文档、提示词和实测结论和代码一样重要。

## 动手之前

先开一个 Issue，说清你想改什么、在哪个模型上验证过。改动只涉及错字或链接时可以直接提 PR。

## skill 的写法

`skills/` 下的内容会直接交给使用者的 Agent 读，按下面几条写：

- **自包含。** 不引用、不依赖任何外部 skill，需要的方法写进本集合。
- **只写结论。** 不写日期、人名、具体项目的路径，也不写"实测""复盘"这类过程记录和内部待办。实测过程写在 Issue 或 PR 描述里。
- **注明适用模型。** 提示词和写法只在验证过的模型上成立，写清是哪个模型。
- **认可过的提示词逐字保存。** 不凭记忆重写，改动时只在出问题的那一句上改。
- **每个子 skill 只写本环节特有的东西。** 跨环节的规则写在 `skills/nuwa/`，视频通用规则写在 `skills/nuwa-motion/`，其他 skill 链接过去，不复制。

新结论写到哪：

| 内容 | 位置 |
|---|---|
| 模型能力、参数、有效和翻车的写法 | `skills/nuwa/references/model-capabilities.md` |
| 参考图怎么分工 | `skills/nuwa/references/reference-roles.md` |
| 服装合成示例 | `skills/nuwa-wardrobe/references/examples.md` |
| 场景配方 | `skills/nuwa-set/references/scene-recipes.md` |
| 视频生成通用规则 | `skills/nuwa-motion/` |
| 某种内容形式的写法和示例 | 对应的形式分支，比如 `skills/nuwa-dance/` |
| 新的内容形式 | 新建 `skills/nuwa-<形式>/`，并在 `skills/nuwa-studio/SKILL.md` 的形式表里登记 |
| 问题和修法 | `skills/nuwa-polish/references/failure-atlas.md` |

被新结论推翻的旧规则直接改掉，不要让两条矛盾的规则同时留着。改 `SKILL.md` 的 `description` 时，想清楚会不会和其他 skill 抢触发。

更完整的维护规则见 [AGENTS.md](./AGENTS.md)。

## 脚本

脚本放在各 skill 的 `scripts/` 下，只依赖 Python 3 标准库和 Pillow（`image-upscale` 例外）。改完至少在本地跑一次 `--help` 和一个真实样例。

## 不要提交的东西

密钥、带签名的接口地址、账号信息、具体项目的文件路径和批次记录，以及你没有权利公开的人像和素材。
