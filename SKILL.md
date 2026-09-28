---
name: design-md
description: 取用 DESIGN.md 设计系统生成视觉一致的 UI——内置 VoltAgent/awesome-design-md 的 74 个品牌设计语言（Linear、Stripe、Notion、Claude、Apple、Tesla、Spotify、Vercel、Ferrari 等），联网拉取配色/字体/圆角/间距/组件 token，落到 CSS 变量后生成 HTML 或组件代码；也支持从任意网站或截图提取生成一份自定义 DESIGN.md。当用户说"用 XX 的风格做个页面/落地页/组件""照着 Linear 的调性设计""参考 Stripe 的视觉""给我一套配色""统一这几个页面的风格""生成/编写 DESIGN.md""照这个网站的风格来做"时使用。
---

# design-md · 设计系统取用与套用

`DESIGN.md` 是 Google Stitch 提出的概念：`AGENTS.md` 管"怎么建"，`DESIGN.md` 管"长什么样"。
本 skill 实时从 `VoltAgent/awesome-design-md`（MIT）拉取 74 个品牌的设计系统，并把其中的
token 落成可直接使用的 CSS 变量。**不落本地副本、不需要 GitHub token。**

统一用这个变量调用脚本（绝对路径，勿用系统 python 3.9.6）：

```bash
DM="/Users/liyanji/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
/Users/liyanji/.workbuddy/skills/design-md/scripts/design_md.py"
```

## 何时触发

- 用：用户指定某个品牌或某种气质要产出 UI；要一套配色/视觉规范；要统一既有页面的观感；要从某站点或截图总结设计语言。
- 不用：纯逻辑/后端/算法改动；用户已提供自家设计规范（此时优先读项目里已有的 `DESIGN.md`）。

## 工作流 A · 套用品牌设计系统生成 UI

**上下文三段式投喂，绝不默认整份灌入**（单份 4–44KB，一次整套 ≤ 8K tokens）。

1. `$DM search "<用户原话>"` → 取 top1。命中多个且气质差异大时，把候选连同「一句话气质」列给用户选，不要自作主张。
2. `$DM fetch <brand>` → 先看**格式 A/B** 与实际章节清单，不要急着读正文。
3. `$DM fetch <brand> --css-vars` → 拿到确定性 CSS 变量。**这一步必须走脚本，禁止你手抄 hex**（最容易出错、最影响观感）。
4. `$DM fetch <brand> --section overview,dos` → 读语气与禁忌（约 1–2KB）。
5. 按需补读：落地页 → `--section components,layout,elevation`；表单/组件 → `--section components`；要适配移动端 → `--section responsive`。
6. 写单文件 HTML：`<style>` 里放第 3 步的 `:root`，**全部样式只用 `var(--md-*)`，禁止出现字面 hex**。字体按 [references/token-mapping.md](references/token-mapping.md) 补回退链。
7. 机械校验（用脚本判定，不靠目测）：
   - `$DM contrast <ink> <canvas>`、`$DM contrast <on-primary> <primary>` ≥ 4.5:1
   - `grep -o '#[0-9a-fA-F]\{6\}' out.html | sort -u` 必须全部出现在 `--css-vars` 输出里（无编造色）
   - 圆角/间距必须命中 `rounded`/`spacing` 标度（禁止 13px 这类野值）
   - 强调色用量符合 Do's and Don'ts（如 Linear：薰衣草蓝只能用在品牌标、焦点环、主 CTA）
   - 只有暗色主题的品牌（Linear 明确禁亮色）**不要臆造亮色版**
8. 交付时在文件头注释写明来源 URL 与 MIT 归属。

> 若第 2 步显示 **format B**，第 3 步的 token 是启发式抽取（`source: heuristic`），必须再读一遍 `--section colors,typography` 复核色值后再生成。

## 工作流 B · 从任意网站 / 截图提取 DESIGN.md

1. `$DM probe-site <url>` → 客观证据：CSS 自定义属性、色值词频、字体栈、圆角分布、阴影、容器宽度（约 8KB）。
2. 若报「suspected CSR」或证据稀疏 → 改用内置 **WebFetch** 工具取渲染后内容；或请用户给 1–2 张截图，用 Read 读图后从图像提色。
3. 按 [references/design-md-template.md](references/design-md-template.md) 合成：先填 frontmatter（colors/typography/rounded/spacing/components），再写 9 段正文，**正文用 `{colors.canvas}` 引用 token**。
4. 写到**目标项目根目录** `./DESIGN.md`（用户指定路径时以指定为准）。
5. `$DM lint ./DESIGN.md` 必须全绿。不确定的角色就留空并在 Known Gaps 说明，**不要编值**。

## 关键陷阱（务必遵守）

- **库里有两种格式**。A（64 个）带 YAML frontmatter，章节是 `Overview / Colors / … / Known Gaps`；B（10 个：kraken, lamborghini, lovable, mastercard, runwayml, sanity, spotify, starbucks, tesla, theverge）无 frontmatter，是 `## 1. … ## 9.` 老格式。用 `--section` 的 canonical key（`overview colors typography components layout elevation shapes dos responsive agent`）可跨两种格式取用，传错会打印该品牌真实章节清单。
- **正文里几乎没有字面 hex**。A 格式正文写的是 `{colors.primary}` 这类占位符，真实值只在 frontmatter。只喂正文 = 拿不到任何颜色。所以第 3 步不可跳过。
- **品牌名 ≠ 目录名**。`Linear`→`linear.app`、`Mistral`→`mistral.ai`、`任天堂`→`nintendo-2001`、`戴尔90年代`→`dell-1996`、`BMW M`→`bmw-m`。**不要猜 URL**，走 `$DM fetch`，它已做六层模糊匹配；不确定时会列候选并退出（code 2）。
- **网络会抖**。`raw.githubusercontent.com` 实测会间歇性超时。脚本按 `references/mirrors.json` 的顺序逐源降级（你的 Gitee 镜像 → 你的 GitHub 镜像 → 官方 raw → jsDelivr），全部失败退出码 3，**此时明确告知用户，绝不杜撰设计 token**。

## 命令参考

```bash
$DM list [--category fintech] [--format names|json]   # 离线，74 个品牌
$DM search "我要做金融后台" [--top 3] [--json]          # 离线，按气质词/别名推荐
$DM fetch <brand>                                     # 元信息：格式、体积、章节清单
$DM fetch <brand> --css-vars                          # :root{--md-color-primary:…}
$DM fetch <brand> --tokens-only | --json              # 解析后的完整 token
$DM fetch <brand> --section overview,dos              # 只取小节
$DM fetch <brand> --out ./DESIGN.md                   # 写入项目根目录
$DM contrast "#f7f8f8" "#010102"                      # → 19.61:1 AAA
$DM lint ./DESIGN.md                                  # 校验自产 DESIGN.md
$DM probe-site https://example.com [--json]           # 站点取证
$DM sync-brands [--stdout|--write]                    # 上游新增品牌时补索引
$DM mirrors                                           # 查看拉取源配置
```

退出码：`0` 成功｜`1` lint 未通过｜`2` 品牌未找到（附最接近候选）｜`3` 网络失败｜`4` 文档格式异常

## 边界

- 只从 `references/mirrors.json` 里配置的源取数，不擅自换源、不编造 token。
- 这是**风格灵感参考**，不是像素级复刻；品牌名仅用于归属说明，产出应面向内部或个人项目。
- 生成物需注明来源 `https://github.com/VoltAgent/awesome-design-md` 及其 MIT 协议。
- 不落本地缓存，离线环境要明确告知无法取数。

索引与模板细节按需再读：`references/brands.md`（74 行品牌索引）、`references/design-md-template.md`（生成模板）、`references/token-mapping.md`（CSS 落地规则）。
