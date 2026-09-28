# design-md

把 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 的 74 套品牌设计系统，
变成 AI 编程助手（WorkBuddy / CodeBuddy / Claude Code 等）能直接调用的**设计系统 skill**。

> `AGENTS.md` 告诉 AI **怎么建**，`DESIGN.md` 告诉 AI **长什么样**。
> 这个 skill 让你可以直接说"用 Linear 的风格做个定价页"，然后拿到一套视觉一致、颜色可追溯的页面。

---

## ⚠️ 归属声明 / Attribution（基于哪个项目）

**本仓库是基于 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 二次封装的，不是原创设计数据。**

| 项目 | 说明 |
|---|---|
| **上游数据源** | https://github.com/VoltAgent/awesome-design-md |
| **上游协议** | **MIT License** — Copyright (c) the awesome-design-md authors |
| **上游做了什么** | 从各品牌公开站点分析、整理出 74 份 `DESIGN.md`（配色 / 字体 / 圆角 / 间距 / 组件 / 响应式 / 该做不该做） |
| **本仓库做了什么** | ① 把这些 `DESIGN.md` 镜像一份（目录 `design-md/`，与上游同构）；② 在其上写了一套零依赖 CLI 与 AI skill，负责检索、解析、把 token 落成 CSS 变量、以及从任意网站反推设计系统 |
| **版权** | 所有设计令牌与文档内容著作权归原作者及各品牌方所有，本仓库**不主张任何权利**；`DESIGN.md` 是 Google Stitch 提出的设计系统文档格式 |
| **用途限制** | 风格灵感参考，非像素级复刻。产出物请注明来源与 MIT 协议，建议用于内部或个人项目 |

镜像数据"原样"提供（as is），不含任何担保。

---

## 📦 安装教程

### 前置条件

- macOS / Linux，Python 3.9+（仓库脚本用标准库写成，**无需 pip install 任何东西**）
- 支持 Skills 的 AI 编程助手（WorkBuddy / CodeBuddy 等，技能目录 `~/.workbuddy/skills/`）

### 方式一：命令行安装（推荐）

```bash
# 1. 克隆本仓库
git clone https://github.com/iahua1004/DESIGN.md.git /tmp/design-md-install
# 国内网络可以用 Gitee：
# git clone https://gitee.com/iahua1004/DESIGN.md.git /tmp/design-md-install

# 2. 复制到技能目录（目录名必须是 design-md，要和 SKILL.md 里的 name 字段一致）
mkdir -p ~/.workbuddy/skills
rm -rf ~/.workbuddy/skills/design-md
mkdir -p ~/.workbuddy/skills/design-md
cd /tmp/design-md-install
cp -R SKILL.md agents references scripts ~/.workbuddy/skills/design-md/

# 3. 验证
~/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  ~/.workbuddy/skills/design-md/scripts/design_md.py list | tail -1
# 输出：(74 brands)   ← 说明装好了
```

> **注意**：如果你的 Python 不在上面那个路径，改成 `python3` 即可（脚本只用标准库，3.9 以上都能跑）。

### 方式二：手动安装

在 [Releases](../../releases) 或仓库页面下载 ZIP，解压后把 `SKILL.md`、`agents/`、`references/`、`scripts/`
四个东⻄复制到 `~/.workbuddy/skills/design-md/` 下即可。

### 方式三：只想要数据，不装 skill

直接用 `design-md/<品牌>/DESIGN.md`，把它复制到你的项目根目录，然后告诉 AI"照这份 DESIGN.md 做页面"。
这是 Google Stitch 的原始用法，不需要任何工具。

### 卸载

```bash
rm -rf ~/.workbuddy/skills/design-md
```

---

## 🚀 使用说明

### 最推荐的用法：直接用自然语言

装好后不用记命令，直接跟 AI 说：

```
用 Linear 的风格做一个三栏定价页
参考 Stripe 的视觉重做这个落地页
我要做个金融后台，专业一点
照着任天堂 2001 那个味儿做个页面
根据 example.com 的风格，给我这个项目写一份 DESIGN.md
```

也可以显式呼叫：`$design-md 用 Tesla 的风格做个落地页`。

### 三个典型场景

**① 指定品牌 → 生成 UI**
`search` 定位品牌 → `--css-vars` 取 token → 读 Do's/Don'ts → 生成只用这些 token 的 HTML。
你不用记目录名："特斯拉"→`tesla`、"任天堂"→`nintendo-2001`、"Mistral"→`mistral.ai` 都能命中。

**② 只有气质、没有品牌 → 先推荐**
说出"金融后台""AI 工具落地页"这类描述，会给出候选（金融 → Stripe / Coinbase / Wise / Revolut）让你挑。

**③ 从任意网站 / 截图反推一套设计系统**
`probe-site` 取证（CSS 变量、色值词频、字体栈、圆角、阴影）→ 套模板合成 `DESIGN.md` → `lint` 校验 →
写进项目根目录，之后这个项目所有页面都保持一致。

### 命令速查

```bash
DM="python3 ~/.workbuddy/skills/design-md/scripts/design_md.py"

$DM list                              # 列出全部 74 个品牌
$DM list --category fintech           # 只看某一类（ai/devtools/backend/saas/design/fintech/commerce/media/auto/retro）
$DM search "我要做金融后台"             # 按气质/别名推荐，带评分
$DM fetch linear                      # 元信息：格式、体积、实际章节清单
$DM fetch linear --css-vars           # ★ 直接可用的 :root{--md-color-primary:#5e6ad2; …}
$DM fetch linear --tokens-only        # 完整 token（JSON）
$DM fetch linear --section overview,dos   # 只取某几节，省上下文
$DM fetch linear --out ./DESIGN.md    # 拷一份到当前项目根目录
$DM contrast "#f7f8f8" "#010102"      # 对比度 → 19.61:1 AAA
$DM probe-site https://example.com    # 场景③ 的取证
$DM lint ./DESIGN.md                  # 校验自己写的 DESIGN.md
$DM sync-brands                       # 上游新增品牌时更新索引
$DM mirrors                           # 查看/调整拉取源
```

**退出码**：`0` 成功｜`1` lint 未通过｜`2` 品牌未找到（会列出最接近的候选）｜`3` 网络失败｜`4` 文档格式异常

### 为什么色值一定要走 `--css-vars`

上游文档正文里写的是 `{colors.primary}` 这类占位符，**真实 hex 只存在于 YAML frontmatter**。
（实测 Linear 的正文有 98 个占位符，却只有 19 个字面 hex。）
所以生成页面时色值一律取自 `--css-vars` 的脚本输出，不要手写、也不要让 AI 凭印象抄——这是最容易出错、
也最影响观感的一步。

---

## 🗂 目录结构

```
design-md/
├── README.md                 ← 你正在看的这份
├── LICENSE                   ← MIT（含上游归属说明）
├── SKILL.md                  ← skill 入口，AI 靠它的 description 判断何时加载
├── agents/openai.yaml        ← 界面元信息
├── references/
│   ├── brands.md             ← 74 个品牌索引（list/search 的唯一数据源）
│   ├── design-md-template.md ← 生成新 DESIGN.md 的模板
│   ├── token-mapping.md      ← token → CSS 变量的落地规则（含字体回退链）
│   └── mirrors.json          ← 拉取源配置
├── scripts/
│   ├── design_md.py          ← 主 CLI（单文件，零第三方依赖）
│   └── mirror.sh             ← 把上游数据同步到你自己仓库的脚本
└── design-md/<品牌>/DESIGN.md ← 74 份镜像数据（与上游目录同构）
```

---

## ⚡ 可选：把自己的仓库配成加速源

`raw.githubusercontent.com` 在国内会间歇性超时。本仓库已经把 74 份数据镜像好了，
把它配成首选源就能绕开这个问题：

编辑 `~/.workbuddy/skills/design-md/references/mirrors.json`，把前两项目前的 `enabled` 改成 `true`，
并填你的仓库地址：

```json
{ "name": "gitee",         "enabled": true,
  "url": "https://gitee.com/iahua1004/DESIGN.md/raw/main/design-md/{dir}/DESIGN.md" },
{ "name": "github-mirror", "enabled": true,
  "url": "https://raw.githubusercontent.com/iahua1004/DESIGN.md/main/design-md/{dir}/DESIGN.md" }
```

脚本会按顺序尝试：**Gitee → GitHub 镜像 → 上游官方 raw → jsDelivr**，全失败才报错（退出码 3），
**绝不会编造设计 token**。

---

## ❓ 常见问题

**Q：需要 GitHub Token 吗？**
不需要。数据全部是公开仓库的 raw 文件，脚本用标准库直接取。

**Q：品牌视觉是精确复刻吗？**
不是。上游是从公开站点分析出的"风格特征"，用来保证**观感一致**，不是像素级还原。

**Q：某些品牌的颜色和我想的不一样？**
上游文件里有 10 个是老格式（kraken / lamborghini / lovable / mastercard / runwayml / sanity /
spotify / starbucks / tesla / theverge），没有结构化 token，颜色是从正文里启发式抽出来的
（输出会标注 `source: heuristic`）。这类品牌建议再读一遍 `--section colors,typography` 核对。

**Q：能离线用吗？**
默认实时联网。如果需要离线，配好上面的镜像源后仍可联网取；真正离线的话把
`design-md/` 目录留着手工取用即可。

**Q：数据多久更新一次？**
跑一次 `$DM sync-brands` 就能看上游有没有新增品牌；有就用 `--write` 补进索引。

---

## 📄 许可

本仓库脚本与文档部分采用 **MIT License**。
镜像数据来自 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)，
同样遵循 **MIT**，著作权归原作者及各自品牌方所有。详见 [LICENSE](LICENSE)。
