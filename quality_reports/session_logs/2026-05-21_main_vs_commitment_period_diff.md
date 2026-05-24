# Main vs Commitment Period 分支对比：数据处理与 Bug 修复

**日期:** 2026-05-21
**对比分支:** `main` (synced with upstream IDAES/idaes-gtep) vs `commitment_period`
**对比范围:** `gtep_data.py`, `gtep_model.py`, `driver_coal.py`

---

## 背景

鸭哥在 commitment_period 分支上搞了 17 轮 debug，把整个 pipeline 从 `load_prescient` 一直修到 `create_model ✅ → BigM ✅`（详见 process_log_0520.md）。现在想搞清楚：哪些 fix 上游 main 也有同样的 bug 可以贡献回去，哪些 main 上的改进可以反哺 commitment_period。

## 一、代码架构差异

| 维度 | main | commitment_period |
|---|---|---|
| 模型代码组织 | 拆分到 `gtep/model_library/` 下多个文件 | 全在 `gtep_model.py` 一个文件（3600+ 行） |
| 数据参数所有权 | `ExpansionPlanningData.__init__` 接收时间参数 | 时间参数在 `ExpansionPlanningModel.__init__` |
| 代码量差异 | 模型文件更精简 | `gtep_model.py` +3608 行 / -402 行 |

main 做了模块化重构（投资、调度、承诺、目标函数等拆到独立文件），commitment_period 保持单文件"先跑起来再说"的状态。

---

## 二、`gtep_data.py` 数据加载差异

### 2.1 `load_prescient` — 硬编码 vs 参数化

| 维度 | main | commitment_period |
|---|---|---|
| `options_dict` | 用户可传入，有默认值 | 硬编码写死 |
| `start_date` | 不显式设置 | 硬编码 `"01-01-2019"` |
| `sced_frequency_minutes` | 从 prescient_options 读取 | 硬编码 `60` |
| `num_time_steps` | 从 `simulation_objects.csv` 动态算 | 硬编码 `24 * 365` |
| `representative_dates` | 参数化（可传入） | 硬编码 2019 年日期 |
| `representative_weights` | 参数化字典 | 硬编码 `{1: 91, 2: 91, 3: 91, 4: 91}` |
| `Path` 对象支持 | 有 | 无 |

**结论:** main 更灵活，commitment_period 太多硬编码。但 commitment_period 的方式目前够用（只跑 Texas case study）。

### 2.2 `time_keys` 修复 (Prescient 2.2.2 兼容)

- **commitment_period ✅ / main ❌**
- 问题: `gridx-prescient 2.2.2` 不自动把 `time_keys` 转成日期字符串，导致后续 `time_keys.index(date)` 找不到匹配
- Fix: 检查 key 是否是纯数字，如果是则手动生成日期字符串做 fallback
- **可 upstream**

### 2.3 `import_load_scaling` — zone 命名

- **main**: 数字 ID `"1"` ~ `"8"`
- **commitment_period**: 地理名 `"COAST"` ~ `"WEST"`

不是 bug，是数据格式依赖。commitment_period 的数据文件用地理名，main 可能用了更新的数据格式。两者各自匹配各自的输入数据即可。

### 2.4 `texas_case_study_updates` — GEN UID 类型转换

- **commitment_period ✅ / main ❌**
- **Bug 1:** pandas 读 gen.csv 时 GEN UID 可能是 int 类型，但 generator dict 的 key 是 str → 永远匹配不上
  - Fix: `generator_df["GEN UID"] = generator_df["GEN UID"].astype(str)`
- **Bug 2:** `float(generator_df[...][col])` 在空匹配时对空 Series 调 `float()` → `TypeError`
  - Fix: `matched.iloc[0]` + empty check
- **严重程度: 高** — main 会直接 crash
- **可 upstream**

### 2.5 `non_fuel_startup_cost` 缺失

- **commitment_period ✅ / main ❌**
- 问题: 某些 generator 数据缺少 `non_fuel_startup_cost` 字段 → `model_data_references` 中 KeyError
- Fix: `setdefault("non_fuel_startup_cost", 0)` 兜底
- **可 upstream**

### 2.6 `"Texas" or "Coal" not in data_path` 逻辑 bug

- **main ❌** — `if "Texas" or "Coal" not in data_path:` 永远为 True（`"Texas"` 是 truthy）
- **commitment_period** — 直接删了这个检查
- **严重程度: 低** — 只是无效检查，不影响执行结果

### 2.7 `load_default_data_settings` 防御性检查

- **main ✅ / commitment_period ❌**
- main 有 `if "elements" in self.md.data.keys()` 和 `if "fuel" in ...keys()` 的检查
- commitment_period 直接访问，key 不存在就炸
- **可从 main 借鉴**

---

## 三、`gtep_model.py` 模型构建差异

### 3.1 `renewableCapacityNameplate` 计算

- **main**: 取**所有** representative period 数据中 `p_max` 的最大值
  ```python
  max([max(m.data_list[i].data["elements"]["generator"][renewableGen]["p_max"]["values"])
       for i in range(len(m.data_list))])
  ```
- **commitment_period**: 只看第一个 representative period 的 `p_max`
  ```python
  max(m.md.data["elements"]["generator"][renewableGen]["p_max"]["values"])
  ```
- **main 更正确** — nameplate capacity 应为全时段最大值。commitment_period 可能低估某些可再生能源的 nameplate capacity。
- **可从 main 借鉴**

### 3.2 `rampUpRates` / `rampDownRates` 单位

- **main**: `units=u.MW / u.minutes` — 但实际数据存的是百分比（如 0.1 = 10%/period），单位标注**不正确**
- **commitment_period**: `units=u.dimensionless` — 更准确
- **commitment_period 的方式更正确**，main 可能导致 Pyomo 单位检查混乱

### 3.3 `commitmentPeriodLength` / `dispatchPeriodLength` / `periodLength` mutable

- **commitment_period ✅ / main ❌**
- commitment_period 加了 `mutable=True`，允许 2hr/4hr driver 在运行时修改时间参数
- 对应的 `pyo.value()` wrapping 也只在 commitment_period 上
- main 不需要这个（没有 2hr/4hr driver）

### 3.4 Stage-specific cost params (`fixedCost1/2/3` 等)

- **commitment_period ✅ / main ❌**
- 问题: ESR WIP 重构（commit `dfce77d`）删了 `fixedCost1/2/3`, `varCost1/2/3`, `fuelCost1/2/3` 的声明，但保留了 `investment_stage_rule` 里使用它们的代码
- Fix: 在 `model_data_references` 中恢复声明，从 generator data 读 `fixed_ops1/2/3` 等字段
- **严重程度: 高** — main 配 `scale_texas_loads=True` 会直接 crash
- **可 upstream**

### 3.5 Block 层级引用

- **commitment_period ✅ / main ❌ (可能)**
- `b.load_scaling` → `i_p.load_scaling`（load_scaling 在 investmentStage block 而非 commitmentPeriod block）
- `b.loads` → `c_p.loads`（loads 在 commitmentPeriod block 而非 dispatchPeriod block）
- main 有相同的 block 结构，如果跑 Texas case study 也会遇到同样的问题

### 3.6 Storage guard

- **commitment_period ✅ / main ❌**
- 问题: 没有 `storage.csv` 时 `m.storage` Set 不创建 → 引用时 AttributeError
- Fix: `hasattr(m, "storage")` guard
- main 的 `storage.py` 模块里也没有这个 guard

---

## 四、总结

### 可贡献回 upstream (main) 的修复

| # | 修复 | 严重程度 | 文件 |
|---|---|---|---|
| 1 | GEN UID `astype(str)` + `iloc[0]` 空匹配保护 | **高** | `gtep_data.py` |
| 2 | `non_fuel_startup_cost` `setdefault` 兜底 | **高** | `gtep_data.py` |
| 3 | `fixedCost1/2/3` 等 stage-specific cost params 恢复 | **高** | `gtep_model.py` |
| 4 | `time_keys` Prescient 2.2.2 兼容 | **中** | `gtep_data.py` |
| 5 | Block 层级引用修正 (`load_scaling`, `loads`) | **中** | `gtep_model.py` |
| 6 | Storage `hasattr` guard | **中** | `gtep_model.py` |
| 7 | `rampUpRates` 单位应为 `dimensionless` | **低** | `gtep_model.py` |
| 8 | `"Texas" or "Coal"` 逻辑 bug | **低** | `gtep_data.py` |

### 可从 main 借鉴的改进

| # | 改进 | 优先级 |
|---|---|---|
| 1 | `renewableCapacityNameplate` 取全时段最大值 | **高** — 影响模型正确性 |
| 2 | `load_prescient` 参数化 | **低** — 目前够用 |
| 3 | `load_default_data_settings` 防御性检查 | **低** |
| 4 | 代码模块化到 `model_library/` | **低** — 等功能稳定后再重构 |

### 当前 Pipeline 状态

```
commitment_period 分支:
load_prescient ✅ → texas_case_study ✅ → model_data_refs ✅ → investment_stages ✅
→ commitment_period ✅ → dispatch ✅ → create_model ✅ → BigM ✅ → solve ❌ (Gurobi 环境问题)
```

模型构建和 BigM 变换已全部通过，卡在 CRC 上 `GurobiDirect` 找不到 Gurobi solver binary。这是环境配置问题，不是代码 bug。下一步：排查 CRC Gurobi 环境或先用 HiGHS 验证模型可行性。
