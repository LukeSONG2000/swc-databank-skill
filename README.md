# 星球大战译名查询

**StarWarsChina Glossary**

一个实时查询星球大战中文网译名的 AI Skill，适合核对翻译、字幕和稿件中的星战专名。支持中英互查、批量查询、类别筛选和分页，优先返回完全匹配的词条。

## 安装与使用

需要 Git、Python 3 和访问原站的网络。在 Codex 中使用时，将仓库克隆到技能目录。

```sh
git clone https://github.com/LukeSONG2000/swc-glossary-skill.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/star-wars-china-glossary"
```

安装后可以在 Codex 对话中这样查询。

> 用 $star-wars-china-glossary 核对 Darth Vader 和 Millennium Falcon 的中文译名。

也可以在仓库目录运行查询脚本，获取 JSON 结果。

```sh
python3 scripts/lookup.py -- 'Darth Vader' '千年隼号'
```

## 来源与社区

译名数据来自星球大战中文网的《星球大战译名管理系统》。感谢南方战士和星球大战中文网维护这套译名资料。[原站译名系统](http://starwarschina.com/glossary/)

欢迎加入星球大战中文网论坛，一起交流星战译名、翻译和作品。[加入论坛](http://starwarschina.com/forum.php)
