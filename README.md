# 星球大战中文网数据库

**StarWarsChina Database**

这个 AI Skill 接入星球大战中文网的译名管理系统和资料库。[主站入口｜星球大战中文网](http://www.starwarschina.com/)

## 子功能

### glossary 译名管理系统

实时核对星战专名，支持中英互查、批量查询、类别筛选和分页，优先返回完全匹配的词条。[子功能入口｜星球大战译名管理系统](http://starwarschina.com/glossary/)

译名数据来自星球大战译名管理系统。感谢南方战士和星球大战中文网维护这套译名资料。

### databank 资料库

按中英文名称检索角色、地点、飞船等分类索引，也可按条目 ID 或链接读取主帖正文。索引和正文来自星球大战中文网。[子功能入口｜资料库（Databank）索引](https://www.starwarsfans.cn/portal.php?mod=list&catid=13)

## 安装与使用

需要 Git、Python 3 和访问原站的网络。在 Codex 中使用时，将仓库克隆到技能目录。

```sh
git clone https://github.com/LukeSONG2000/swc-databank-skill.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/swc-databank-skill"
```

安装后可以在 Codex 对话中这样查询。

> 用 $swc-databank-skill 核对 Darth Vader 和 Millennium Falcon 的中文译名。

> 用 $swc-databank-skill 在资料库找千年隼号，并概述条目里的设定。

也可以在仓库目录运行脚本，获取 JSON 结果。

```sh
python3 scripts/lookup.py -- 'Darth Vader' '千年隼号'
python3 scripts/databank.py categories
python3 scripts/databank.py search --category 星际飞船 -- '千年隼号'
python3 scripts/databank.py read 14227
```

## 从仓库更新

通过 Git 安装后，可以在 Codex 中说「用 $swc-databank-skill 从仓库更新这个 Skill」，或运行以下命令。

```sh
git -C "${CODEX_HOME:-$HOME/.codex}/skills/swc-databank-skill" pull --ff-only
```

如果安装在其他目录，将命令中的路径改为实际的仓库目录。

## 论坛

欢迎加入星球大战中文网论坛，一起交流星战译名、翻译和作品。[加入论坛](http://starwarschina.com/forum.php)
