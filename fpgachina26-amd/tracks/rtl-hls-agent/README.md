# RTL/HLS 本地智能体设计赛道

提交一套可本地部署的完整方案，含开源权重模型、推理栈、智能体、技能包和基线脚本，
在断网沙箱中自主完成从读题到产出代码的全过程。两个 track 分别产出 Verilog 和
C++，**独立排名、独立评奖，推荐只选其一**。

赛道要求、提交内容与评分权重见 [GUIDE.md](GUIDE.md)。

---

## 取参考仓库

两个 track 各有一个参考仓库，选定 track 后克隆对应的那个：

```bash
# HLS track：产出 Vitis HLS C++
git clone https://gitee.com/Vickyiii/hlsagent2026

# RTL track：产出 Verilog / SystemVerilog
git clone https://gitee.com/Vickyiii/rtlagent2026
```

两个仓库结构相同，内容按 track 特化：

| 目录 | 内容 |
| --- | --- |
| `example/` | 一套能完整跑起来的最小示范方案，按提交结构组织，可直接作起点 |
| `tasks/` | 3 道示例题，格式与评测题集同形 |
| `selftest/` | 本地分级判定与算分脚本，与赛事方使用同一份判定器 |
| `docs/API_CONTRACT.md` | 接口契约。评测当天赛事方按它向你的服务投题，赛前固定 |
| `docs/FAQ.md` | 常见问题 |
| `SCORING.md` | 评分细则：分级系数、四项权重、增益公式与算分示例 |
| `REPORT_TEMPLATE.md` | 设计报告模板 |

---

## 第一天先做什么

仓库根目录的 `README.md` 里有完整的开发—验证—提交闭环。最短路径是这三步：

```bash
cd example
pip install -r requirements.txt

# ① 桩模式：不联网、不要 key，验证 run.sh 的输入输出契约是否贯通
LLM_BACKEND=mock ./run.sh ../tasks/<示例题> /tmp/out

# ② 接入自备的 LLM API，确认智能体循环能跑
export LLM_BACKEND=openai LLM_BASE_URL=<你的端点> LLM_API_KEY=<key>
./run.sh ../tasks/<示例题> /tmp/out

# ③ 装好 Vivado / Vitis 之后，跑一遍分级判定
cd ../selftest && cp env.sh.example env.sh && ./run_selftest.sh --reference
```

第 ③ 步的 `--reference` 用参考实现验证判定链路，不依赖模型与 key。**这一步不过，
后面所有分数都不可信。**

---

## 三件容易被忽略的事

**基线脚本不得修改。** `run_baseline.sh` 与 `baseline.py` 由赛事方提供，是增益项的
分母。没有可运行的基线，这一项不得分。

**开发期可用商用 API，提交时不行。** 决赛在断网沙箱中运行，`MODEL.md` 中声明的必须
是可本地部署的开源权重。示范方案已把 LLM 后端设计为可替换，开发、验证与提交三个阶段
共用同一份智能体代码，差异只在几个环境变量。

**参考测试台不下发给智能体。** 判定功能正确性所用的测试台由赛事方掌握。生成过程中
如何自我验证，属于本赛道拟考察的内容之一。
