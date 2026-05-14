# VASP 不收敛排查手册（SCF + 结构优化）

> 资料来源：基于 VASP 官方 Wiki 中关于 `ALGO / IALGO / AMIX / BMIX / IMIX / NELMDL / IBRION / POTIM / SMASS / EDIFF / EDIFFG` 等的说明，并结合计算化学公社（bbs.keinsci.com）社区中常见的 VASP 收敛性讨论与 Sobereva 等长期沉淀的经验整理。
> 使用原则：**先电子，后离子；每次只改 1~2 个参数；先能收敛，再追精度。**

---

## 1. 三种典型“不收敛”的判别

| 现象 | 关键特征 | 优先方向 |
|---|---|---|
| **SCF 不收敛** | `OSZICAR` 中 `NELM` 步打满，`dE` 长期 ~1e-3 起伏 | 调 `ALGO`、`AMIX/BMIX`、`ISMEAR/SIGMA`、初猜 |
| **结构优化不收敛** | 每步 SCF 能收敛，但力/能量长期降不下去 | 调 `IBRION`、`POTIM`、分阶段 `ISIF`、`EDIFFG` |
| **离子一动电子就炸** | 几何动一下 SCF 就崩 | 先稳电子（更稳的 `ALGO`、更密 K、更合适展宽）；离子步用更小 `POTIM` |

> Wiki 提示：`EDIFF` 必须比 `EDIFFG` 严格——力是基于已收敛 SCF 计算的；`EDIFF` 过松会让“力”本身就含噪。

---

## 2. SCF 不收敛：按优先级排查

### 2.1 选对 `ALGO`（最常用第一手段）

VASP Wiki 推荐：
- `ALGO = Normal`（blocked-Davidson）：**默认首选**，对绝大多数体系最稳。
- `ALGO = Fast`：Davidson + RMM-DIIS 切换，速度快，但金属/磁性/难收敛体系容易振荡。
- `ALGO = VeryFast`：纯 RMM-DIIS，速度最快，最不稳，仅当 `Normal/Fast` 已经稳定时使用。
- `ALGO = All` / `Damped`：杂化泛函（HSE 等）以及顽固绝缘体/磁性体系收敛“最终大杀器”。

经验顺序：
1. `Normal` 跑不稳 → `All`
2. `All` 仍不稳 → 配合 2.4、2.5 的混合参数与初猜重置

另外可尝试 `ALGO = Conjugate`（共轭梯度），对某些体系比 Davidson 更稳。

### 2.2 展宽 `ISMEAR / SIGMA`

VASP Wiki 经典建议：
- 金属：`ISMEAR=1` 或 `2`（Methfessel-Paxton），`SIGMA=0.1~0.2`。
- 半导体/绝缘体：`ISMEAR=0`（高斯展宽），`SIGMA=0.05`（最常用）。
- 高精能量/DOS：`ISMEAR=-5`（四面体法），但**只有结构和电荷已稳**时再用，且 K 点必须够（≥ 4 个不可约 K 点，且非 Γ-only）。
- 绝缘体若用 `-5` 不稳，可临时 `ISMEAR=0, SIGMA=0.05` 把 SCF 稳住，再切回 `-5` 取最终能量。

社区常见提醒：金属直接 `-5` 容易难收敛，且 Wiki 明确说 `-5` 不适合力/应力（即不适合 relax）。

### 2.3 `NELM / NELMDL / NELMIN`

- `NELM`：最大 SCF 步。难体系建议 `120~200`。
- `NELMDL`：起步若干步只更新波函数、不更新电荷。Wiki 建议**新算且初猜不好时设负值**（如 `NELMDL = -10` 表示前 10 步不更新电荷），可显著降低开局振荡。
- `NELMIN`：最少 SCF 步。relax / MD 中建议设 `4~6`，避免“假收敛”。

### 2.4 混合参数 `AMIX / BMIX / IMIX`

VASP Wiki 默认：`IMIX=4`（Pulay），`AMIX=0.4`，`BMIX=1.0`。

调参思路：
- **电荷振荡**：减小 `AMIX`（如 `0.2`），保留 `BMIX=1.0`。
- **大尺寸 slab / 真空层 / 不均匀体系**：Wiki 推荐用 Kerker 强阻尼 → `AMIX=0.2, BMIX=0.0001`。
- **磁性体系**：往往需要更大磁通道更新 → `AMIX_MAG=1.6, BMIX_MAG=1.0`，或同时 `AMIX=0.2, BMIX=0.0001`。
- 若仍不稳：`IMIX=1`（Kerker linear mixing）配合小 `AMIX`，更稳但更慢。

社区常用救命套餐（顽固 slab / 磁性）：
```ini
AMIX     = 0.2
BMIX     = 0.0001
AMIX_MAG = 0.8
BMIX_MAG = 0.0001
```

### 2.5 重置初猜（处理“坏历史”）

按强度递增依次试：
1. `ISTART=1, ICHARG=0`：正常续算。
2. `ISTART=1, ICHARG=1`：用旧 `CHGCAR` 当初猜（结构小改时常用）。
3. `ISTART=0, ICHARG=2`：完全重置，最稳；结构变化大、相变、参数大改时优先这种。

> Wiki 提醒：`WAVECAR`/`CHGCAR` 与当前体系参数（`ENCUT`、网格、并行）不一致时强行复用反而会更差。

### 2.6 磁性 + d/f 元素

- `ISPIN=2` 必须给合理 `MAGMOM`，否则常落入错误磁态。
- 含 d 元素：`LMAXMIX=4`；含 f 元素：`LMAXMIX=6`。这是 Wiki 强制建议；不加常见“能量收敛但磁矩离谱”。
- DFT+U：`LDAU=.TRUE.` + `LDAUTYPE=2` + `LDAUL/LDAUU/LDAUJ`；初始磁矩要给“想要”的极化方向，否则 SCF 难落到正确局部极小。

### 2.7 数值精度与网格

- `ENCUT`：建议至少 `1.3 × ENMAX(POTCAR)`；难收敛或相变体系再上调。
- **预收敛技巧**：先用更小 `ENCUT`（如 `1.0 × ENMAX`）跑通 SCF，再读 `WAVECAR` 逐步恢复到目标 `ENCUT`。反过来，某些体系用更大 `ENCUT` 反而更稳（网格更密、噪声更小），可尝试 `1.5 × ENMAX` 预收敛。
- `PREC = Accurate`：FFT 网格更密，相对 `Normal` 更稳，是提高积分精度的直接手段。
- `ADDGRID = .TRUE.`：增大电荷/势的辅助网格，对硬赝势 / 难收敛体系常有奇效。
- K 点：太稀容易电子噪声大、振荡；金属体系尤其要够密。
- **K 点递进策略**：先用 `1 1 1`（Γ-only）跑通 SCF 并保存 `CHGCAR`，再 `ICHARG=1` 读 `CHGCAR` 用目标高 K 点继续算。这对大晶胞/低对称体系非常有效。

### 2.8 结构优化/MD 中某步突然不收敛

当 relax 或 MD 跑到某一步 SCF 突然炸掉时，增大混合历史：
```ini
MAXMIX = 50   ! 默认 -45，增大可保留更多历史步的电荷信息
```
配合减小 `POTIM` 或临时收紧 `EDIFF` 通常能渡过。

### 2.9 赝势选择

- 硬赝势（如某些 GW 赝势、含半芯态的赝势）天然难收敛。
- 可换更 soft 的赝势（如 `_sv` → `_pv`，或换 `GW` → 普通 PBE 赝势先跑通）。
- 换赝势后必须重新检查 `ENCUT` 收敛性。

### 2.10 体系/几何检查（最容易被忽视）

- 是否有过近原子（< 0.7 倍共价键长）→ 电子直接发散。
- 是否有非常规价态（如初始磁矩与价态不一致）。
- 真空层是否过薄（slab）、是否两端都是金属面（需偶极修正 `LDIPOL/IDIPOL`）。
- 是否有错误的对称性（缺陷、磁有序请 `ISYM=0`）。

---

## 3. 结构优化不收敛：按优先级排查

### 3.1 选对 `IBRION`（VASP Wiki 标准建议）

- `IBRION=2`（CG）：**远离平衡、初始结构差**时最稳。
- `IBRION=1`（RMM-DIIS / 拟牛顿）：**接近平衡**时收敛速度快，但远离平衡会发散。
- `IBRION=3`（damped MD）：极端难收敛、力很大时的兜底——配合较小 `POTIM` 与 `SMASS` 做阻尼。
- `IBRION=-1`：单点。

> Wiki 重点：`IBRION=1` 仅适合二阶展开有效的近平衡区域；力很大时务必先 `IBRION=2` 把结构拉到合理区。

### 3.2 调 `POTIM`

- `IBRION=1/2`：`POTIM` 是步长缩放因子。振荡明显就降低 `POTIM` 值，如 `0.2 → 0.1`。
- `IBRION=3`：`POTIM` 是 fs 量级 MD 步长，常用 `0.1~0.2`，配合 `SMASS=0.4~1.0` 做阻尼。

### 3.3 分阶段放自由度（很有效）

1. **阶段 1**：`ISIF=2` 只放原子位置。
2. **阶段 2**：`ISIF=3` 再开晶胞。
3. 软材料 / 层状 / 大应变体系，直接 `ISIF=3` 极易在原子-晶胞之间耦合振荡。

> Wiki 提醒：当晶胞维度变化较大时，要重新生成 K 网格 / 重启计算（`ENCUT` 由 `PREC` 自动算的网格会变），否则 Pulay stress 会污染应力。

### 3.4 收敛阈值分两级

- 粗优化：`EDIFFG=-0.05`，先把结构拉到合理区域。
- 精优化：`EDIFFG=-0.02`。
- `EDIFF` 始终比 `EDIFFG` 严格至少 1~2 个量级（如 `EDIFF=1E-5` 配 `EDIFFG=-0.05`）。

### 3.5 约束与边界条件

- Slab：固定底层若干层（Selective Dynamics）防止整体漂移。
- 吸附：远离活性位点的衬底原子可先冻结。
- 分子/团簇：注意整体平移/转动 → 加大盒子或固定一个原子。

### 3.6 应力异常处理

- 应力长期 GPa 级以上：先检查初始晶胞是否离谱（如错放参数、错误单位）。
- 先 `ISIF=2` 把原子摆顺，再放 `ISIF=3`。
- HSE/精算 ISIF=3 之前，建议先用 PBE 把晶胞优化到比较接近的状态。

### 3.7 离子一动 SCF 就炸

通常是“电子还没真稳”或 `POTIM` 太大：
- 提升电子稳定性（按第 2 节排查）。
- 减小 `POTIM`。
- 暂时收紧 `EDIFF`，让每步力更准。


---

## 4. 症状 → 对症（速查）

| 症状 | 对症动作 |
|---|---|
| `NELM` 每步打满 | `ALGO=Normal/All/Conjugate`；加 `NELMDL=-10`；重置 `ISTART/ICHARG`；放宽 `EDIFF` |
| 能量锯齿/振荡 | 减小 `AMIX`；改 `IMIX=1`；调 `ISMEAR/SIGMA` |
| 磁矩飞或假收敛 | 给合理 `MAGMOM`；加 `LMAXMIX=4/6`；调 `AMIX_MAG/BMIX_MAG` |
| Slab/界面 SCF 难收敛 | `AMIX=0.2, BMIX=0.0001`；查真空层；考虑 `LDIPOL` |
| 杂化（HSE）不收敛 | `ALGO=All` 或 `Damped`；先 PBE 收敛后 `ICHARG=1` 起步 |
| 力降不下去 | `IBRION=2` → 接近平衡再 `IBRION=1`；减 `POTIM`；分级 `EDIFFG` |
| 某步突然不收敛 | `MAXMIX=50`；减 `POTIM`；临时收紧 `EDIFF` |
| 硬赝势难收敛 | 换更 soft 赝势；`ADDGRID=.TRUE.`；降 `AMIX` |
| 离子一动电子炸 | 先稳电子；减小 `POTIM`；暂时收紧 `EDIFF` |
| 应力长期偏大 | 检查初始晶胞；先 `ISIF=2` 再 `ISIF=3`；K 点足够密 |

---

## 6. 进阶技巧汇总

以下技巧来自社区实战经验，按适用场景分类：

| 技巧 | 适用场景 | 操作 |
|---|---|---|
| 提高积分精度 | SCF 振荡、力不准 | `PREC = Accurate` |
| 提高格点精度 | 硬赝势、难收敛 | `ADDGRID = .TRUE.` |
| K 点递进 | 大晶胞直接高 K 点不收敛 | 先 `1 1 1` 跑通 → 存 `CHGCAR` → `ICHARG=1` 切高 K 点 |
| 换 ALGO | Davidson 不稳 | 试 `ALGO = Conjugate` 或 `All` |
| 增大混合历史 | relax/MD 中某步突然不收敛 | `MAXMIX = 50` |
| ENCUT 预收敛 | 高 `ENCUT` 直接跑不稳 | 先用更小（或更大）`ENCUT` 跑通再恢复 |
| 换赝势 | 硬赝势天然难收敛 | 换更 soft 赝势（`_sv` → `_pv` 等） |

## 7. 工程建议

- 每次只改 1~2 个参数，便于定位真正有效项。
- 保留 `OUTCAR / OSZICAR / vasprun.xml`，做对比复盘。
- 难体系标准节奏：**粗 → 稳 → 精**，分阶段比一把梭稳得多。
- 做参数敏感性测试（`ENCUT` / K 点）时，固定其他参数。
