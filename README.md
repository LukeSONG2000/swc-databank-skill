# 星球大战中文网数据库

**StarWarsChina Database**

这个 AI Skill 接入星球大战中文网的公开查询服务。目前只有下列子功能。[主站入口｜星球大战中文网](http://www.starwarschina.com/)

## 子功能

### glossary 译名管理系统

实时核对星战专名，支持中英互查、批量查询、类别筛选和分页，优先返回完全匹配的词条。[子功能入口｜星球大战译名管理系统](http://starwarschina.com/glossary/)

译名数据来自星球大战译名管理系统。感谢南方战士和星球大战中文网维护这套译名资料。

## 安装与使用

需要 Git、Python 3 和访问原站的网络。在 Codex 中使用时，将仓库克隆到技能目录。

```sh
git clone https://github.com/LukeSONG2000/swc-databank-skill.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/swc-databank-skill"
```

安装后可以在 Codex 对话中这样查询。

> 用 $swc-databank-skill 核对 Darth Vader 和 Millennium Falcon 的中文译名。

也可以在仓库目录运行查询脚本，获取 JSON 结果。

```sh
python3 scripts/lookup.py -- 'Darth Vader' '千年隼号'
```

## 论坛

欢迎加入星球大战中文网论坛，一起交流星战译名、翻译和作品。[加入论坛](http://starwarschina.com/forum.php)
