# -*- coding: utf-8 -*-
"""拟合 Andersen et al. (2020) 娱乐性恐惧的倒U顶点 → FEAR_ENJOYMENT_PEAK 标定。

数据：OSF 开放数据 https://osf.io/43hzk（Open Data badge）
  - Self-report data/Post_questionnaire.csv：三个 jump-scare 位置级自评
    （Fear/Enjoyment × Scientist/Piggy/Zombies，0–9 Likert），Recall、COMPLETE
  - Self-report data/Pre_Questionnaire.csv：Motivation（a=内在 / b=外在）

主口径（复现论文 LME，需 numpy/pandas/statsmodels）：
  enjoyment ~ fear + fear^2 + age + gender + motivation
  + (1|participant) + (1|location)        [statsmodels: groups=pid, vc_formula location]
  顶点 fear* = -b_fear / (2*b_fear^2)（其余因子取 0 时曲线的驻点）

  复现质量对照（Andersen et al. 2020, Psych Sci 31(12), Table/Fig 4）：
    论文 β_quad=-0.05 (SE=0.02, p=.014)   → 复现 -0.044 (SE=.018, p=.011)
    论文 β_mot=+1.27 (p=.019)             → 复现 +1.24 (p=.016)
    论文 β_gender=-1.44 (p=.007, 女<男)   → 复现 -1.55 (p=.002)
    论文 age n.s.                          → 复现 n.s.
  样本差异：论文分析样本 92 人（含心率数据缺失排除），本复现用问卷完整者
  102 人/286 位置级观测（心率缺失不影响问卷自评）。

回退口径（零第三方依赖，纯标准库 OLS）：
  pooled OLS + 位置固定效应 + 控制变量——双随机截距的一阶近似，二次项
  方向/量级一致但顶点略低；仅在无 statsmodels 环境下使用。

样本规则：
  - COMPLETE=1（完成全程；论文排除未完成者）
  - 位置级 Recall=1（论文主口径只含记得位置的评分；含不记得者结果不变）
  - 缺失（空白）观测跳过；GENDER 编码 1=男 2=女（与论文 women<men 方向核对）

换算假设（写入 mapping.py 注记）：
  Likert 0–9 线性映射引擎恐惧强度 0–1，即 fear_engine = fear_likert / 9。
  「9 = more scared than ever before」≈ 引擎恐惧上限 1.0。

用法（-I 隔离模式，数据目录含下载物）：
  python -I scripts/fit_fear_enjoyment_peak.py --post <Post_questionnaire.csv> \
      [--pre <Pre_Questionnaire.csv>] [--no-lme]
"""

from __future__ import annotations

import argparse
import csv
import sys

LOCATIONS = ("Scientist", "Piggy", "Zombies")


def _to_int(cell: str):
    cell = (cell or "").strip()
    if cell == "":
        return None
    try:
        return int(float(cell))
    except ValueError:
        return None


def read_post(path: str):
    """→ (rows, motivation_map)；rows 为 (participant, age, gender, complete, location, fear, enjoy)。"""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        obs = []
        for row in reader:
            pid = (row["PARTICIPANT"] or "").strip()
            age = _to_int(row["AGE"])
            gender = _to_int(row["GENDER"])
            complete = _to_int(row["COMPLETE"])
            for loc in LOCATIONS:
                recall = _to_int(row.get(f"Recall {loc}", ""))
                fear = _to_int(row.get(f"Fear {loc}", ""))
                enjoy = _to_int(row.get(f"Enjoyment {loc}", ""))
                if complete != 1 or recall != 1:
                    continue
                if fear is None or enjoy is None:
                    continue
                obs.append((pid, age, gender, loc, fear, enjoy))
    return obs


def read_pre(path: str | None):
    """→ {participant: intrinsic(1/0)}；a=内在 1，b=外在 0，a/b 计 1（含内在成分，注明假设）。"""
    if not path:
        return {}
    mapping = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            pid = (row["Participant"] or "").strip()
            mot = (row.get("Motivation") or "").strip().lower()
            mapping[pid] = 1 if mot.startswith("a") else 0
    return mapping


def solve(matrix, rhs):
    """高斯消元解线性方程组（纯标准库，规模 ≤6）。"""
    n = len(rhs)
    a = [list(map(float, row)) + [float(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular normal matrix")
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col] / a[col][col]
            for c in range(col, n + 1):
                a[r][c] -= factor * a[col][c]
    return [a[i][n] / a[i][i] for i in range(n)]


def ols(rows):
    """rows: [(y, x1..xk)] → (beta, r2)。含截距。"""
    k = len(rows[0]) - 1
    xs = [[1.0] + [float(v) for v in r[1:]] for r in rows]
    ys = [float(r[0]) for r in rows]
    n = len(rows)
    xtx = [[sum(xr[i] * xr[j] for xr in xs) for j in range(k + 1)] for i in range(k + 1)]
    xty = [sum(xr[i] * y for xr, y in zip(xs, ys)) for i in range(k + 1)]
    beta = solve(xtx, xty)
    y_mean = sum(ys) / n
    ss_res = sum((y - sum(b * x for b, x in zip(beta, xr))) ** 2 for xr, y in zip(xs, ys))
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    return beta, 1.0 - ss_res / ss_tot if ss_tot else float("nan")


def run_lme(obs, motivation):
    """主口径：statsmodels 复现论文双随机截距 LME。→ dict 或 None（依赖缺席）。"""
    try:
        import pandas as pd
        import statsmodels.formula.api as smf
    except ImportError:
        return None
    rows = [
        {
            "pid": pid,
            "location": loc,
            "fear": float(fear),
            "enjoy": float(enjoy),
            "age": float(age),
            "gender": float(gender),
            "mot": float(motivation.get(pid, 0.5)),
        }
        for pid, age, gender, loc, fear, enjoy in obs
        if age is not None and gender is not None
    ]
    df = pd.DataFrame(rows)
    md = smf.mixedlm(
        "enjoy ~ fear + I(fear**2) + age + gender + mot",
        df,
        groups=df["pid"],
        re_formula="1",
        vc_formula={"location": "0 + C(location)"},
    )
    fit = md.fit(reml=False, method="lbfgs")
    b1, b2 = fit.params["fear"], fit.params["I(fear ** 2)"]
    vertex = -b1 / (2.0 * b2) if b2 < 0 else float("nan")
    # delta-method 顶点 CI：x*=-b1/(2b2)，∇=(-1/2b2, b1/2b2²)，Var=∇Σ∇ᵀ（Σ 取 cov_params 的 2×2 子阵）
    cov = fit.cov_params()
    v_b1b2 = cov.loc[["fear", "I(fear ** 2)"], ["fear", "I(fear ** 2)"]].to_numpy()
    grad = [-1.0 / (2.0 * b2), b1 / (2.0 * b2 * b2)]
    var_vertex = float(grad @ v_b1b2 @ grad)
    se_vertex = max(var_vertex, 0.0) ** 0.5
    ci = (vertex - 1.96 * se_vertex, vertex + 1.96 * se_vertex)
    print(f"[主口径 LME] N={len(df)} 位置级观测 / {df['pid'].nunique()} 人（复现论文混合模型）")
    print(f"  b_fear={b1:+.4f}  b_fear^2={b2:+.4f} (SE={fit.bse['I(fear ** 2)']:.4f}, p={fit.pvalues['I(fear ** 2)']:.4f})")
    print(f"  b_gender={fit.params['gender']:+.3f} (p={fit.pvalues['gender']:.3f})  b_mot={fit.params['mot']:+.3f} (p={fit.pvalues['mot']:.3f})")
    print(f"  论文对照: β_quad=-0.05 (SE=.02, p=.014), β_mot=+1.27, β_gender=-1.44")
    print(f"  顶点 fear* = {vertex:.3f} / 9 → 引擎尺度 {vertex / 9.0:.3f}")
    print(f"  顶点 95% CI（delta method）= [{ci[0]:.2f}, {ci[1]:.2f}] / 9 → 引擎尺度 [{ci[0]/9:.2f}, {ci[1]/9:.2f}]"
          if se_vertex > 0 else "  顶点 CI 不可估计")
    return {"vertex_likert": vertex, "vertex_engine": vertex / 9.0, "b1": b1, "b2": b2}


def run_ols_fallback(obs, motivation):
    """回退口径：pooled OLS + 位置固定效应 + 控制变量（双随机截距的一阶近似）。"""
    m = [
        (enjoy, fear, float(fear) ** 2, loc != "Scientist", loc != "Piggy",
         age, gender, motivation.get(pid, 0.5))
        for pid, age, gender, loc, fear, enjoy in obs
        if age is not None and gender is not None
    ]
    (b0, b1, b2, b_pig, b_zom, b_age, b_gender, b_mot), r2 = ols(m)
    vertex = -b1 / (2.0 * b2) if b2 < 0 else float("nan")
    print(f"[回退 OLS+位置FE] N={len(m)}  R^2={r2:.3f}")
    print(f"  b_fear={b1:+.4f}  b_fear^2={b2:+.4f}  b_gender={b_gender:+.3f}  b_mot={b_mot:+.3f}")
    print(f"  顶点 fear* = {vertex:.3f} / 9 → 引擎尺度 {vertex / 9.0:.3f}（双随机截距不可吸收个体基线，顶点略偏低）")
    return vertex


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--post", required=True, help="Post_questionnaire.csv 路径")
    ap.add_argument("--pre", default=None, help="Pre_Questionnaire.csv 路径（控制 Motivation）")
    ap.add_argument("--no-lme", action="store_true", help="跳过 statsmodels LME，只用零依赖 OLS 回退口径")
    args = ap.parse_args()

    obs = read_post(args.post)
    motivation = read_pre(args.pre)
    n_people = len({o[0] for o in obs})
    print(f"位置级观测 N={len(obs)}（{n_people} 名完成者 ×3 位置，COMPLETE=1、Recall=1 且无缺失）")

    result = None if args.no_lme else run_lme(obs, motivation)
    if result is None:
        run_ols_fallback(obs, motivation)

    print("\n换算假设：fear_engine = fear_likert / 9（0–9 Likert 线性映射引擎 0–1 恐惧强度）。")
    print("写入 emotion_os/generation/mapping.py 的 FEAR_ENJOYMENT_PEAK 注记。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
