# VASP 后处理简明教程

> 涵盖：Bader 电荷 / 功函数 / NEB 与 Slow-Growth / ELF / COHP。
> 每节给出关键 INCAR、运行步骤、输出文件与易错点。

---

## 1. Bader 电荷分析

**目的**：把电子总数按 Bader 体积分到每个原子，给出原子电荷转移。

**INCAR 关键设置**：
```ini
PREC   = Accurate
LCHARG = .TRUE.
LAECHG = .TRUE.       ! 写 AECCAR0 (核电荷) + AECCAR2 (价电荷)
NGXF   = 2*NGX        ! 推荐加密 FFT 网格 (或 NGYF/NGZF)
LWAVE  = .FALSE.      ! 可省空间
LREAL  = .FALSE.      ! Bader 推荐用倒空间投影
```

**运行步骤**：
1. 跑一次普通 SCF，生成 `CHGCAR`、`AECCAR0`、`AECCAR2`。
2. 合并全电荷：
   ```bash
   chgsum.pl AECCAR0 AECCAR2     # 输出 CHGCAR_sum
   ```
3. 调 Henkelman `bader`：
   ```bash
   bader CHGCAR -ref CHGCAR_sum
   ```
4. 读 `ACF.dat` 第 5 列 `CHARGE`：
   - 转移电荷 = `ZVAL(POTCAR)` − `CHARGE`。

**易错点**：
- 忘了 `LAECHG`，得到的是“价电荷 Bader”，不是全电荷 Bader → 数值偏小。
- FFT 网格太粗 → 体积分错；建议 `NGXF/NGYF/NGZF` 加倍。
- `LREAL=Auto` 会让电荷有微小误差，精算关掉。

---

## 2. 功函数（slab）

**目的**：求 `Φ = E_vac − E_F`。

**几何要求**：
- Slab + 真空层 ≥ 15 Å（不对称表面要更厚）。
- 若上下表面不等价 → 必加偶极修正。

**INCAR 关键设置**：
```ini
LVHAR  = .TRUE.       ! 输出局域静电势 LOCPOT (Hartree)
LVTOT  = .FALSE.
LDIPOL = .TRUE.       ! 偶极修正 (不对称 slab 必开)
IDIPOL = 3            ! 真空方向 (一般 z)
DIPOL  = 0.5 0.5 0.5  ! 体心分数坐标即可
ISMEAR = 0
SIGMA  = 0.05
LWAVE  = .FALSE.
LCHARG = .TRUE.
```

**运行步骤**：
1. SCF 收敛，得到 `LOCPOT` 与 `OUTCAR`。
2. 沿 z 方向做平面平均（VASPKIT、`vtotav.py`、或自写）：
   ```bash
   vaspkit -task 426    # VASPKIT: planar average of LOCPOT
   ```
3. 真空区平台值 = `E_vac`；从 `OUTCAR` 取 `E-fermi`。
4. `Φ = E_vac − E_F`（双面不等价时分别取上/下平台）。

**易错点**：
- 真空不够厚 → 平台不平、`Φ` 偏低。
- 不对称 slab 没开 `LDIPOL` → 两面 `Φ` 串扰。
- 用 `LVTOT` 而不是 `LVHAR`：前者含 XC 势，不是标准做法。

---

## 3. NEB（CI-NEB）

**目的**：找过渡态 (TS) 与最小能量路径 (MEP)。需要 VTST tools。

**目录结构**：
```
neb/
├── 00/POSCAR   ! 反应物 (已优化)
├── 01/POSCAR   ! image 1
├── ...
├── 0N/POSCAR   ! image N
├── 0(N+1)/POSCAR  ! 产物 (已优化)
├── INCAR
├── KPOINTS
└── POTCAR
```

**生成中间像**：
```bash
nebmake.pl 00/POSCAR 0(N+1)/POSCAR N
```

**INCAR 关键设置**：
```ini
IMAGES  = 5           ! 中间像数 (不含两端)
SPRING  = -5          ! 标准弹簧 (CI-NEB 用 -5)
LCLIMB  = .TRUE.      ! 爬坡 NEB (找 TS)
ICHAIN  = 0           ! NEB 链
IBRION  = 3
POTIM   = 0           ! 力由 NEB 接管
IOPT    = 1 / 2 / 3   ! VTST 优化器: 1=LBFGS, 2=CG, 3=QM
EDIFFG  = -0.05       ! 力收敛 (NEB 略松)
NSW     = 200
ISYM    = 0           ! 关对称
LWAVE   = .FALSE.
LCHARG  = .FALSE.
```

**后处理**：
```bash
nebresults.pl         # 出 neb.dat / mep.eps / exts.dat
nebef.pl              # 各像能量+力
```

**易错点**：
- 两端没收敛到力 < `|EDIFFG|`，全程都难收敛。
- 像太少 → 抓不到 TS 曲率；像太多 → 慢且易漂。
- 忘 `LCLIMB=.TRUE.` → 只得到光滑 MEP，没有真正 TS。
- 用了对称 (`ISYM≠0`)：路径会被对称化破坏。

---

## 4. Slow-Growth（约束反应坐标）

**目的**：沿给定**集合变量 (CV)** 缓慢拉动，得到自由能/PMF。需要 VASP + `ICONST`。

**典型 CV**：键长、键角、二面角、配位数。文件 `ICONST` 例：
```
R 1 2 0      ! 原子1-2距离, 状态0=约束
```
状态码：`0` 固定值；`7` slow-growth（按 `INCREM` 改变）。

**INCAR 关键设置**：
```ini
IBRION  = 0           ! MD
MDALGO  = 2           ! Nose-Hoover (NVT)
SMASS   = 0
ISIF    = 2
POTIM   = 0.5         ! fs
TEBEG   = 300
NSW     = 5000+
LBLUEOUT = .TRUE.     ! 输出 REPORT 中的拉格朗日乘子
INCREM   = 0.001      ! CV 每步增量 (与 ICONST 状态7配合)
ISYM    = 0
```

**运行流程**：
1. 平衡 NVT (CV 约束在初值，状态 `0`)。
2. 切换 `ICONST` 中状态为 `7`，给定 `INCREM`，跑 slow-growth。
3. 由 `REPORT` 中的 ⟨λ⟩ 对 CV 积分得到 ΔF：
   `ΔF(ξ) = ∫ ⟨λ(ξ′)⟩ dξ′`。

**易错点**：
- `INCREM` 太大 → 非平衡功偏大，PMF 偏离。
- 平衡时间不足 → 起点带偏置。
- 多 CV 时要注意 Fixman 修正（Blue-Moon）。

---

## 5. ELF（电子局域化函数）

**目的**：判断键合类型（共价/孤对/离域）。`ELF ∈ [0,1]`，`>0.7` 偏共价/孤对。

**INCAR 关键设置**：
```ini
LELF   = .TRUE.       ! 输出 ELFCAR
NPAR   = 1            ! VASP5 写 ELF 的硬性要求 (老版本)
PREC   = Accurate
LWAVE  = .FALSE.
LCHARG = .TRUE.
```

**运行 & 可视化**：
1. 普通 SCF 后得 `ELFCAR`。
2. 用 VESTA / VASPKIT / py4vasp 可视化等值面。
   ```bash
   vaspkit -task 333    # ELF 平面/线分布
   ```

**易错点**：
- 老版本 VASP **必须** `NPAR=1`，否则 `ELFCAR` 全零或乱。
- 网格过粗 → 等值面锯齿；可加 `NGXF` 等。

---

## 6. COHP / COOP（成键分析）

**目的**：基于投影分子轨道分析键合（成键/反键贡献）。需 LOBSTER。

**VASP 端 INCAR**（先跑一次 SCF，**保留波函数**）：
```ini
ISTART = 0
ICHARG = 2
ISYM   = -1           ! LOBSTER 不喜欢对称化波函数
LWAVE  = .TRUE.       ! 必须保留 WAVECAR
LCHARG = .TRUE.
PREC   = Accurate
NSW    = 0
NBANDS = ...          ! 必须 ≥ LOBSTER basis 所需 (lobsterin 会报数)
ISMEAR = 0
SIGMA  = 0.05
```

**LOBSTER 端**：
1. 写 `lobsterin`：
   ```
   COHPstartEnergy  -10
   COHPendEnergy     5
   basisSet         pbeVaspFit2015
   cohpBetween atom 1 atom 2
   cohpBetween atom 1 atom 3
   ! 也可: cohpGenerator from 1 to 4 type O type H
   ```
2. 在 VASP 输出目录运行：
   ```bash
   lobster
   ```
3. 输出：
   - `COHPCAR.lobster` → 画 -COHP(E)（负为成键）
   - `COOPCAR.lobster` → COOP
   - `ICOHPLIST.lobster` → 积分到 `E_F` 的键强排序
   - `CHARGE.lobster` → Mulliken/Löwdin 电荷
   - `lobsterout` → **必看**，确认 `Total spilling < ~5%`

**易错点**：
- `ISYM ≠ -1`：LOBSTER 报 “Wave functions are symmetrized”。
- `NBANDS` 不够：`lobsterout` 会提示需要的最小值，按其重跑 VASP。
- spilling > 10% → basis 与赝势不匹配，换 `basisSet` 或检查 POTCAR。
- 忘了 `LWAVE=.TRUE.`，没有 `WAVECAR` 啥都干不了。

---

## 速查总表

| 分析 | 关键开关 | 主要输出 | 配套工具 |
|---|---|---|---|
| Bader | `LAECHG=.T., LCHARG=.T.`, 加密 NGXF | `AECCAR0/2`, `CHGCAR` | `chgsum.pl`, `bader` |
| 功函数 | `LVHAR=.T., LDIPOL=.T., IDIPOL=3` | `LOCPOT`, `OUTCAR` | VASPKIT / 自写 |
| NEB | `IMAGES, LCLIMB=.T., IBRION=3, POTIM=0, IOPT` | `0i/OUTCAR`, `neb.dat` | VTST `nebmake/results.pl` |
| Slow-growth | `IBRION=0, MDALGO=2, LBLUEOUT=.T., INCREM`, `ICONST` | `REPORT` | 自写积分脚本 |
| ELF | `LELF=.T.` (+老版 `NPAR=1`) | `ELFCAR` | VESTA / VASPKIT |
| COHP | `ISYM=-1, LWAVE=.T., NBANDS` | `WAVECAR` → LOBSTER | `lobster` |
