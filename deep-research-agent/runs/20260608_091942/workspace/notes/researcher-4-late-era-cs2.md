# CS:GO 后期运营与 CS2 过渡 (2020-2023) — 研究笔记

## 1. 疫情时代玩家爆发（2020-2021）

- 2020年3月：首次突破 100 万同时在线。2020年4月：1,305,714 峰值。 [src_7d753a, src_0b369c] [strong]
- 2020年2月月均 58 万+，同比增长 55%。F2P + 疫情居家共同驱动。 [src_0b369c] [medium]
- 2023年2月11日：1,320,219 新高（CS2 发布前夕）。2022年回落至约 100 万（峰值 1,013,237）。 [src_7d753a] [strong/medium]

## 2. Operation Shattered Web（2019.11 – 2020.03）

- 第 9 次 Operation，首次引入 Agents 系统（CT/T 角色皮肤，任意地图装备）。 [src_aca8c2, src_c06708] [strong]
- 首次采用 Battle Pass 格式，含每周任务、可升级硬币、新武器收藏品、贴纸、新箱子。 [src_d05f0a, src_5f2d63] [strong]
- SSG 553（SG 553）被削弱。 [src_c06708] [medium]

## 3. Operation Broken Fang（2020.12 – 2021.05）

- 延续 Battle Pass 模式，新增每周任务、新饰品、统计数据追踪。 [src_0e6d90, src_796489] [medium]
- 引入 Retakes（回防）游戏模式。 [src_0e6d90] [medium]
- ⚠️ 具体武器收藏品、地图轮换列表未充分获取。

## 4. Operation Riptide（2021.09 – 2022.02）

- 第 11 次 Operation。全新任务系统（每周任务卡片，任意顺序完成），新地图、Agents、武器收藏品。 [src_241eb4] [strong]
- Private Queue（私人队列）：Queue Code 在 Valve 官方服务器进行私人 Premier 比赛。 [src_241eb4] [strong]
- 短时竞技（Shorter Competitive）选项。 [src_241eb4] [medium]

## 5. Source 2 引擎迁移传闻

- Valve 2015 年公布 Source 2，同年 Dota 2 移植。社区持续猜测 CS:GO 也将升级。 [src_135c1c] [strong]
- 2020-2022 年间数据挖掘者多次在更新文件中发现 Source 2 字符串。爆料者 Gabe Follower 持续追踪。 [src_8a95ec] [medium]
- ⚠️ 泄露时间线不够精细。

## 6. CS2 正式公布与 Limited Test（2023.03）

- 2023.03.22：Valve 正式公布 Counter-Strike 2——CS:GO 免费升级版，基于 Source 2。"CS 历史上最大的技术飞跃"。 [src_0dee93, src_70f08f, src_353cc9] [strong]
- Limited Test 当日启动，邀请制逐步扩大。原计划"2023年夏季"正式发布。 [src_0dee93, src_f0057a, src_e28f88] [strong]

## 7. CS2 正式发布（2023.09.27）

- CS2 正式上线，直接取代 Steam 上 CS:GO。CS:GO 不再作为独立商店产品，库存全部迁移。 [src_353cc9, src_9792bf, src_acff97] [strong]
- 发布当日峰值约 150 万同时在线，创 CS 系列新高。 [src_62c93d] [medium]

## 8. CS2 核心技术改进

- **Sub-tick 系统**: 取代传统固定 tick rate（64/128）。记录每次操作的精确时间戳，在 tick 间传送。官方服务器 64Hz，但 sub-tick 理论上消除"动作落于 tick 间"的问题。 [src_0488e4, src_6f5341, src_21ea84] [strong]
- **Source 2 渲染**: 改进的渲染管线、光照、材质、物理。经典地图分"Full Overhaul"（完全重建）与"Touchstone"（精准保留+光照升级）。 [src_353cc9, src_55d5aa] [medium]
- **烟雾弹物理（Volumetric Smoke）**: 动态体积烟雾，可与环境交互——被子弹/手雷爆炸驱散、受力影响、形状随空间变化。最受关注的影响力变化。 [src_c24e5f, src_5fa781, src_3894ad] [strong]

## 9. 社区反应

- **正面**: 画质大幅提升、体积烟雾增加战术深度、免费升级、库存无缝继承。 [src_353cc9] [medium]
- **批评**: 性能优化不佳（中低配机器 FPS 下降）、sub-tick 手感不如真 128-tick（多位职业选手失望）、首发缺少大量 CS:GO 模式与地图、创意工坊不完整。 [src_4aaeb0, src_32124a, src_c34df1] [medium]

## 10. CS:GO Legacy 版本

- 可通过 Steam 库→属性→Betas→`csgo_legacy` 下载旧版 CS:GO。 [src_be48cc, src_4528c4, src_cc1aaf] [strong]
- 用途：观看旧 Demo、社区服务器/旧模组、怀旧。无更新、无官方匹配、无运营活动。 [src_be48cc] [strong]
- 全部皮肤和库存物品在 CS2 中保留并自动适配 Source 2 渲染。 [src_be48cc, src_2dd966] [medium]

## 待验证观察
- ⚠️ KitGuru 报道 180 万并发 vs Fragster 132 万——以 Steam Charts 数据为准
- ⚠️ Operation Riptide 结束日期存在来源笔误（2021年5月 vs 实际应为 2022年2月）
