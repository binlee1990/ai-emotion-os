Task format: 2
Objective: ai-emotion-os v0.7：打包收尾——pyproject.toml（setuptools，零运行时依赖）+ __version__ + examples 去 sys.path hack（try import / 仓库内 fallback 两全）+ README 安装段 + .gitignore 构建产物；pip install -e . 验证从仓库外目录 import 与全量 pytest。license 字段省略（版权默认保留，未获授权不做法律声明）。
Scope: 输入=v0.6（c89b6f4，已推送）；允许新增 pyproject.toml、改 emotion_os/__init__.py、examples/、README、.gitignore、.tasks；不加运行时依赖；pip 装进用户环境为可逆操作（uninstall 干净移除）。
Success criteria: (1) pip install -e . 成功；(2) 从仓库外目录 python -c "from emotion_os import EmotionEngine" 通过；(3) 安装态下全量 pytest 通过；(4) 仓库内裸跑 examples 仍可用（fallback 路径）；(5) fresh 复审无 P0。
Verification: pip install -e .（--no-build-isolation 优先避免网络）；临时目录 import 探针；python -m pytest tests/ -q；python examples/demo_story.py。
Progress: 已完成：pyproject（复审实证打包范围恰好 21 个 emotion_os/*.py、requires-python>=3.10 经 AST 全文件核对、零依赖声明属实）+ __version__ 0.7.0 + examples 两全 import + 仓库外 import 探针 0.7.0 + 安装态 163 passed + 裸跑回退（python -S）实证；fresh 复审无 P0/P1（1 项 P2 已修：README 发布形态措辞）。待提交推送。
