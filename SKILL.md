---
name: swc-databank-skill
description: 查询星球大战中文网的中英译名和 Databank 资料库。用于核对星战专名、批量统一翻译术语，或检索并阅读角色、地点、飞船等资料库条目。
---

# 星球大战中文网数据库

用 Python 3 运行本技能目录下的脚本。核对译名时用 glossary，查找设定条目或阅读正文时用 databank。[主站入口｜星球大战中文网](http://www.starwarschina.com/)

默认直接给结果，省略来源链接。用户明确索要出处或链接时，在答复末尾统一附上相应原站链接。

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
- 引用时使用 `source.url`。比较不同版本的译法时，写明各自对应的出版物、字幕或地区版本。

## databank 资料库

用 `scripts/databank.py` 按原站分类索引找中英文条目。需要了解设定时，选定搜索结果后读取条目主帖正文。[子功能入口｜资料库（Databank）索引](https://www.starwarsfans.cn/portal.php?mod=list&catid=13)

```sh
python3 scripts/databank.py categories
python3 scripts/databank.py search --category 角色 -- 'Luke Skywalker'
python3 scripts/databank.py read 2527
```

- `search` 返回索引中的并列中英文名称及条目 `id`、`url` 和类别。个别条目直接指向 StarWars.com，返回其链接和空 `id`。`partial` 表示有分类查询失败，具体分类见 `errors`。
- `read` 接受 `id` 或帖子链接。读长文时可将 `next_offset` 传给 `--offset` 继续。根据原文概述所问设定，保留原文标出的版本或连续性背景。
- 资料库索引与译名管理系统的收录范围和译法可能不同。查哪个来源就使用该来源的结果。如果一个译名在资料库索引查不到，可以用 glossary 查英文名后再检索。引用资料时使用条目的 `entry.url`。

## 从仓库更新

用户要求更新本技能时，在其 Git 安装目录执行 `git pull --ff-only`，然后重新读取技能说明。安装方式见 [README](README.md)。
