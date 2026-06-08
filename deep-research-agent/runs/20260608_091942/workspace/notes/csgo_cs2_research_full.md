# CS:GO Late Operations & CS2 Transition — Research Notes

## 1. Pandemic Player Growth (2020-2021)
- April 2020: CS:GO hit 1,305,714 concurrent players (COVID peak)
- February 11, 2023: New all-time record of 1,320,219 concurrent players (pre-CS2 hype)
- February 2020: Average 580k+ players, 55% increase YoY
- March 2020: First surpassed 1M concurrent
- 2022: Hit 1,013,237 concurrent; maintained strong numbers
- Sources: src_7d753a (Fragster), src_0b369c (CalvinAyre), src_3b8b24 (KitGuru - 1.8M claim)

## 2. Operation Shattered Web (Nov 2019 - Mar 2020)
- 9th CS:GO operation, released Nov 18, 2019, ended Mar 30, 2020
- First operation to introduce "Agents" (CT Operators / T Agents), equippable on any map
- First battle pass format operation — weekly missions, earnable cosmetics
- New weapon collections, stickers, graffiti, crates
- SSG 553 nerf (T-side rifle)
- Sources: src_5f2d63 (Fandom Wiki), src_d05f0a (Twinfinite), src_aca8c2 (DMarket), src_c06708 (DotEsports)

## 3. Operation Broken Fang (Dec 2020 - May 2021)
- 10th CS:GO operation
- Continued battle pass format from Shattered Web
- Weekly missions, new cosmetics, stat tracking system
- Introduced "Retakes" game mode (competitive bomb defusal scenario practice)
- Sources: src_0e6d90 (Fandom Wiki), src_796489 (BulletApps)

## 4. Operation Riptide (Sep 2021 - Feb 2022)
- 11th CS:GO operation, released Sep 21, 2021
- New maps, overhauled mission system
- Private Queue: player-generated Queue Code for private Premier matches
- Steam Group Private Queues
- New agents, weapon collections (2021 Mirage Collection), stickers, patches
- Shorter Competitive matches option
- Sources: src_241eb4 (Official counter-strike.net), src_cdf739 (GameSpecifications)

## 5. Source 2 Rumors & Transition
- Source 2 engine announced by Valve in 2015, Dota 2 ported same year
- CS:GO Source 2 port rumored for years; community dataminers found references
- Major leak surfaced on Twitter (reported by talkesport) with Source 2 references
- Gabe Follower (prominent Valve leaker) tracked Source 2 CS:GO strings
- March 2023: Valve officially announced Counter-Strike 2 as free upgrade to CS:GO
- Sources: src_8a95ec (TalkEsport leaks), src_135c1c (Source 2 Wikipedia)

## 6. CS2 Announcement & Limited Test (Mar 2023)
- Announced March 22, 2023
- Limited Test began same day, invite-only for select players
- Tentative full release scheduled for "Summer 2023"
- Described as "largest technical leap" in CS history
- Sources: src_0dee93 (CS2 Wiki), src_70f08f (GameTomatoes), src_353cc9 (PlayTestedReview)

## 7. CS2 Official Release (Sep 27, 2023)
- Released September 27, 2023, replacing CS:GO on Steam
- Free upgrade; CS:GO effectively "sunset" as live product
- Record-breaking concurrent player numbers at launch (~1.5M peak)
- Sources: src_353cc9, src_9792bf (Esports.gg), src_62c93d (Statista)

## 8. CS2 Core Technical Improvements

### Sub-tick System
- Replaced fixed 64-tick / 128-tick server model
- Records exact timestamp of every input event (mouse clicks, movement, shots) between ticks
- Server processes actions with precise time values rather than at fixed intervals
- Official servers run at 64Hz but with sub-tick precision
- Aimed to end the 64-vs-128 tick debate
- Community mixed: more responsive in theory, but not equivalent to 128-tick that pros expected
- Sources: src_0488e4 (XPlay.gg), src_6f5341 (CodeGenes), src_21ea84 (FloatPeak)

### Source 2 Engine
- Full engine migration from Source (2004) to Source 2
- Improved rendering, lighting, materials
- Better performance on modern hardware
- Map remakes/upgrades: Dust II, Mirage, Nuke, Overpass, Italy, Office etc. received Source 2 treatment
- Sources: src_353cc9, src_55d5aa (Wikipedia CS2)

### Volumetric Smoke Grenades
- Smoke now dynamic volumetric objects interacting with environment
- React to lighting, gunfire, and explosions
- Can be temporarily dispersed by gunfire or HE grenades
- Fundamentally changed tactical utility meta
- Sources: src_c24e5f (YouTube - Valve official), src_5fa781 (Strafe), src_3894ad (Tradeit)

## 9. Community Reaction
- Positive: Graphics upgrade, volumetric smokes adding tactical depth, free upgrade model
- Negative: Performance issues (FPS drops, poor optimization on older hardware)
- Sub-tick system: praised for innovation but criticized for not delivering true 128-tick feel
- Missing features at launch: many CS:GO game modes, maps, and workshop tools absent
- Pro players (e.g., m0NESY) shared optimization tricks for better FPS
- Sources: src_4aaeb0 (DotEsports), src_32124a (TalkEsport editorial), src_c34df1 (TikTok trends)

## 10. CS:GO Legacy Version
- CS:GO not available as standalone Steam store product after CS2 launch
- Accessible via CS2 Properties → Betas → "csgo_legacy – Legacy Version of CS:GO"
- Used for: old demo playback, tooling compatibility, classic community servers, nostalgia
- Not a fully supported live game — no updates, no official matchmaking
- All skins/items from CS:GO carried forward to CS2 inventory
- Sources: src_be48cc (Fragster), src_4528c4 (Flavor365), src_cc1aaf (Tradeit), src_eba90f (Steam Community)
