---
name: swc-databank-skill
description: 接入星球大战中文网的公开查询服务，目前提供实时译名查询。用于中英译名互查、核对星球大战角色、地名、飞船、组织等专名，以及为翻译、字幕、文章或资料批量统一术语。
---

# 星球大战中文网数据库

StarWarsChina Database 的主站是星球大战中文网，目前提供译名查询。[主站入口](http://www.starwarschina.com/)

## 译名查询

用 Python 3 运行本技能目录下的 `scripts/lookup.py`。每个参数是一个独立的中文或英文词条。先用完整专名，查询多个词条时各自传入。

```sh
python3 scripts/lookup.py -- 'Darth Vader' 'Millennium Falcon' '绝地委员会'
python3 scripts/lookup.py --category 人物 -- 'Darth Vader'
python3 scripts/lookup.py --page 2 -- 'Jedi'
```

脚本调用译名管理系统的公开表单，每次返回一页 JSON。类别可用 `--help` 查看，页码从 1 开始。[子功能入口｜星球大战译名管理系统](http://starwarschina.com/glossary/)

- 对每个词条优先核对 `match: "exact"` 的结果。用 `english`、`chinese` 和 `category` 判断指代，照录原站的译名、标点和并列写法。仅有 `related` 条目时，将它们作为候选。
- 查某个专名时如果只有候选或 `not_found`，可再试简称、全称或另一语言的写法。宽泛查询可用 `last_page` 判断还有几页。对整段翻译，先提取需要核对的专名再查询。
- `not_found` 表示这次查询无结果。`error` 表示查询未完成，参照 `error_code` 与 `message` 处理。批量查询中，即使脚本报告错误，也应读取 JSON 中其他词条的结果。
- 默认直接给出查到的译名，省略来源链接。用户明确索要出处或链接时，在答复末尾用 `source.url` 标注一次「星球大战中文网译名管理系统」。比较不同版本的译法时，写明各自对应的出版物、字幕或地区版本。
