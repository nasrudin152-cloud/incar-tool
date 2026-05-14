# VASP INCAR 实用速查表

> 按“场景 → 关键参数”组织，便于直接抄改 `INCAR`。

---

## 1. 启动 / 重启（`ISTART`, `ICHARG`）

| 场景 | `ISTART` | `ICHARG` | 需要 `WAVECAR`? | 需要 `CHGCAR`? | 说明 |
|---|---|---|---|---|---|
| 第一次算 | 0 | 2 | 否 | 否 | 由原子叠加电荷起步 |
| 普通续算 | 1 | 0 | 是 | 否 | 从 `WAVECAR` 读波函数 |
| 完全连续重启 | 2 | 0 | 是 | 否 | 保持网格、晶胞等一致 |
| 小改结构后用旧电荷加速 | 0 / 1 | 1 | 可有可无 | 是 | 旧电荷做初猜，加速 SCF |
| 静态 SCF | 1 | 0 | 建议有 | 否 | 结构不变只重新自洽 |
| PBE 能带 | 1 | 11 | 建议有 | **是** | 非自洽，固定电荷 |
| PBE DOS | 1 | 11 | 建议有 | **是** | 同上，配密 K 点 |
| HSE 能带 | 1 | **不用 11** | 建议有 | 不建议固定 | HSE 需要自洽 |

`ICHARG` 速记：
- `0` 由 `WAVECAR` 算电荷
- `1` 读 `CHGCAR` 当初猜
- `2` 原子叠加
- `11` 固定电荷做非自洽（band/DOS）

### 数值含义（简洁版）

| 参数 | 数值 | 一句话含义 |
|---|---|---|
| `ISTART` | `0` | 新算，不读 `WAVECAR` |
| `ISTART` | `1` | 读 `WAVECAR` 继续算 |
| `ISTART` | `2` | 更严格连续重启（要求前后设置更一致） |
| `ICHARG` | `0` | 从 `WAVECAR` 生成电荷并自洽 |
| `ICHARG` | `1` | 读 `CHGCAR` 作为初猜再自洽 |
| `ICHARG` | `2` | 原子叠加电荷起步并自洽 |
| `ICHARG` | `11` | 固定电荷非自洽（常用于 PBE 能带/DOS） |

---

## 2. 电子自洽（SCF）

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `ENCUT` | 1.3 × 最大 ENMAX (POTCAR) | 平面波截断 |
| `PREC` | `Accurate` | 精度等级 |
| `EDIFF` | `1E-6` (relax) / `1E-7` (static) | SCF 收敛阈值 |
| `NELM` | 60–200 | 最大 SCF 步 |
| `NELMIN` | 4–6 | 最少 SCF 步 |
| `ALGO` | `Normal` / `Fast` / `All` (HSE/杂化) | SCF 算法 |
| `ISMEAR` | -5 (绝缘体/DOS), 0 (分子), 1 (金属 MP), 2 (金属 wide) | 占据展宽方法 |
| `SIGMA` | 0.05 (绝缘体) / 0.1–0.2 (金属) | 展宽宽度 |
| `LREAL` | `.FALSE.`(<20 atoms) / `Auto`(>20) | 实空间投影 |
| `LMAXMIX` | 4 (d 元素) / 6 (f 元素) | 电荷混合 l 截断 |
| `AMIX` / `BMIX` | 默认即可，磁性体系常调 | 混合参数 |

---

## 3. 离子驰豫

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `IBRION` | `-1` 静态 / `1` QN(近平衡) / `2` CG(粗糙) / `3` damped MD | 离子更新算法 |
| `NSW` | 0 (静态) / 50–200 (relax) | 离子步数 |
| `ISIF` | `2` 仅原子 / `3` 原子+晶胞 / `4` 体积固定改形状 / `7` 仅体积 | 应力/晶胞自由度 |
| `EDIFFG` | `-0.01`~`-0.03` (eV/Å) | 力收敛阈值（负值=力，正值=能量） |
| `POTIM` | 0.5 (relax) / 1–3 fs (MD) | 步长 |
| `ISYM` | `2` 默认 / `0` 关对称 (磁性、缺陷) | 对称性 |

---

## 4. K 点与积分

| 用途 | 建议 K 点 | `ISMEAR` / `SIGMA` |
|---|---|---|
| 结构优化 | Γ 居中, ka ≈ 30–40 | 1 / 0.1 (金属), 0 / 0.05 (绝缘) |
| 静态 SCF | 比 relax 更密 (×1.5) | -5 / 0.05 (DOS 友好) |
| DOS | 很密 (60+) | -5 / 0.05 |
| 能带 | 高对称路径（line-mode） | 0 / 0.05 |
| 杂化 HSE | 适度 (10–20) + 减小 NKRED | 0 / 0.05 |

---

## 5. 自旋与磁性

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `ISPIN` | `2` (开自旋) | 开关自旋极化 |
| `MAGMOM` | 每元素初猜 | 初始磁矩 |
| `LORBIT` | `11` | 投影 DOS/磁矩输出 |
| `LNONCOLLINEAR` | `.TRUE.` | 非共线磁 |
| `LSORBIT` | `.TRUE.` | 自旋轨道耦合（需 NCL） |
| `LDAU` 系列 | `LDAU=.TRUE.`, `LDAUTYPE=2`, `LDAUL`, `LDAUU`, `LDAUJ` | DFT+U |

---

## 6. 输出与文件

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `LWAVE` | `.TRUE.` (要续算) / `.FALSE.` (省空间) | 是否写 `WAVECAR` |
| `LCHARG` | `.TRUE.` (要 CHG/band) / `.FALSE.` | 是否写 `CHGCAR` |
| `LAECHG` | `.TRUE.` (Bader) | AECCAR 用于 Bader |
| `LVHAR` / `LVTOT` | `.TRUE.` (功函数/势) | 写静电势 |
| `NWRITE` | `2` 默认 / `1` 简洁 | OUTCAR 详细度 |
| `LORBIT` | `10`/`11` | PROCAR 投影信息 |

---

## 7. 杂化与精算

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `LHFCALC` | `.TRUE.` | 开杂化 |
| `HFSCREEN` | `0.2` (HSE06) | 屏蔽长度 |
| `AEXX` | `0.25` | 精确交换比例 |
| `ALGO` | `All` / `Damped` | 杂化推荐算法 |
| `PRECFOCK` | `Fast` / `Accurate` | 交换积分精度 |
| `NKRED` | 2 (粗略) | 减少交换 k 点 |
| `TIME` | 0.4 | Damped 步长 |

---

## 8. AIMD 分子动力学

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `IBRION` | `0` | MD |
| `MDALGO` | `2` Nose-Hoover / `3` Langevin | 系综算法 |
| `SMASS` | `0` 自适应 / `>0` 给定 | Nose 质量 |
| `ISIF` | `2` NVT / `3` NPT | 系综 |
| `POTIM` | 0.5–1.0 (fs) | 时间步长 |
| `NSW` | 1000+ | 步数 |
| `TEBEG` / `TEEND` | 目标温度 (K) | 温度 |
| `LREAL` | `Auto` | 大体系加速 |
| `PREC` | `Low` / `Normal` | MD 通常降低精度 |

---

## 9. 偶极/带电体系

| 参数 | 推荐值 | 含义 |
|---|---|---|
| `LDIPOL` | `.TRUE.` | 偶极修正 |
| `IDIPOL` | `1/2/3` 方向 / `4` 全部 | 修正方向 |
| `DIPOL` | 几何中心分数坐标 | 偶极原点 |
| `NELECT` | 总价电子 ± q | 带电模拟 |
| `EFIELD` | eV/Å | 外加电场 |

---

## 10. 经验规则速记

- **金属**：`ISMEAR=1, SIGMA=0.1~0.2`；DOS 改 `ISMEAR=-5`。
- **绝缘体/半导体**：`ISMEAR=0, SIGMA=0.05` 或 `-5`。
- **分子/团簇**：`ISMEAR=0, SIGMA=0.01~0.05`，单 Γ 点常够。
- **力收敛**：`EDIFFG=-0.02` 配 `EDIFF=1E-6`；不要让 `EDIFF` 比 `EDIFFG` 还松。
- **续算三件套**：`ISTART=1` + 旧 `WAVECAR` + (可选) `CHGCAR`。
- **能带/DOS 标准流程**：先 SCF (写 `CHGCAR`) → 再 NSCF `ICHARG=11` 读 `CHGCAR`。
- **HSE 不可固定电荷**：HSE 必须自洽，禁用 `ICHARG=11`。
- **磁性 + d/f 元素**：必加 `LMAXMIX=4` (d) 或 `6` (f)，否则磁矩、能量错误。
- **大体系**：`LREAL=Auto` 显著加速；超精度算回到 `.FALSE.`。
- **空间不足**：`LWAVE=.FALSE., LCHARG=.FALSE.` 关掉大文件输出。

---
