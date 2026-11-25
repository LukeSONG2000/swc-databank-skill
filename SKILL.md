---
name: swc-databank-skill
description: 当任务涉及《星球大战》的专名或设定时使用，包括答疑、翻译、字幕、写作和内容设计，即使用户没有明确要求查询。主动用星球大战中文网的译名管理系统核对中英专名，需要设定依据时查阅 Databank 资料库。
---

# 星球大战中文网数据库

用 Python 3 运行本技能目录下的脚本。[主站入口｜星球大战中文网](http://www.starwarschina.com/)

回答问题或制作星战内容前，主动提取影响结果的角色、地点、组织、飞船等专名，用 glossary 批量核对译名。需要准确描述原作设定时，用 databank 检索并阅读相关条目，将查到的事实和用语用于成品。保留用户指定的译法、版本和原创命名。

## glossary 译名管理系统

用 `scripts/lookup.py` 查询，每个参数是一个独立的中文或英文词条。先用完整专名，查询多个词条时各自传入。

```sh
python3 scripts/lookup.py -- 'Darth Vader' 'Millennium Falcon' '绝地委员会'
python3 scripts/lookup.py --category 人物 -- 'Darth Vader'
python3 scripts/lookup.py --page 2 -- 'Jedi'
```

脚本调用译名管理系统的公开表单，每次返回一页 JSON。类别可用 `--help` 查看，页码从 1 开始。[子功能入口｜星球大战译名管理系统](http://starwarschina.com/glossary/)

- 对每个词条优先核对 `match: "exact"` 的结果。用 `english`、`chinese` 和 `category` 判断指代，照录原站的译名、标点和并列写法。仅有 `related` 条目时，将它们作为候选。
- 查某个专名时如果只有候选或 `not_found`，可再试简称、全称或另一语言的写法。宽泛查询可用 `last_page` 判断还有几页。对整段翻译，先提取需要核对的专名再查询。
- `not_found` 表示这次查询无结果。`error` 表示查询未完成，参照 `error_code` 与 `message` 处理。批量查询中，即使脚本报告错误，也应读取 JSON 中其他词条的结果。
- 默认直接给译名，省略来源链接。用户明确索要出处或链接时，在答复末尾用 `source.url` 标注一次。比较不同版本的译法时，写明各自对应的出版物、字幕或地区版本。

## databank 资料库

用 `scripts/databank.py` 按原站分类索引找中英文条目。需要了解设定时，选定搜索结果后读取条目主帖正文。[子功能入口｜资料库（Databank）索引](https://www.starwarsfans.cn/portal.php?mod=list&catid=13)

```sh
python3 scripts/databank.py categories
python3 scripts/databank.py search --category 角色 -- 'Luke Skywalker'
python3 scripts/databank.py read 2527
```

- `search` 返回索引中的并列中英文名称及条目 `id`、`url` 和类别。个别条目直接指向 StarWars.com，返回其链接和空 `id`。`partial` 表示有分类查询失败，具体分类见 `errors`。
- `read` 接受 `id` 或帖子链接。读长文时可将 `next_offset` 传给 `--offset` 继续。根据原文概述所问设定，保留原文标出的版本或连续性背景。
- 资料库索引与译名管理系统的收录范围和译法可能不同。查哪个来源就使用该来源的结果。如果一个译名在资料库索引查不到，可以用 glossary 查英文名后再检索。
- **独立条目链接必附。** 在首次答复末尾，用条目名附上每个作为依据或展示给用户的中文网独立页面。检索用对应结果的 `url`（有论坛条目 `id`），阅读用 `entry.url`。每个链接都须直达条目正文，同一条目附一次。补充来源按需附上。

## 从仓库更新

两个查询脚本会为从官方仓库克隆的版本在后台静默检查更新，同一安装目录最多每 24 小时检查一次。更新仅对改动已提交、可快进的 `main` 分支生效。

脚本结果含 `skill_update` 时，完成用户的查询答复后，用一句话提示技能已更新。没有该字段时照常答复。

用户明确要求立即更新时，在本技能的 Git 安装目录执行 `git pull --ff-only`，然后重新读取技能说明。安装方式见 [README](README.md)。
