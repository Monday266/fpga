# FPGAchina26-amd

全国大学生嵌入式芯片与系统设计竞赛 2026 · FPGA 创新设计赛道（AMD）参赛总指南。

本仓库是入口，不含代码。它的作用是告诉你有哪些赛道、你该选哪一个、选定之后去哪里
取材料。各赛道的参考仓库与示范代码在各自的位置，本仓库只做索引与转述。

---

## 三个赛道

| 赛道 | 参赛资格 | 核心考察 | 主要平台 |
| --- | --- | --- | --- |
| [RTL/HLS 本地智能体设计](tracks/rtl-hls-agent/) | 不限 | 本地模型与智能体在硬件设计任务上的通过率与增益 | AMD Radeon 显卡 + Vivado / Vitis |
| [具身智能](tracks/embodied-ai/) | 不限 | 端侧 AI 与 FPGA/Zynq 协同的物理任务闭环 | 任意 AMD AI PC + 任意 AMD FPGA / Zynq / Versal |
| [自主选题（初级组）](tracks/open-topic/) | 大学一年级至三年级在读本科生 | 基本 FPGA 设计能力与作品完整度 | AMD FPGA / Zynq |
| [自主选题（高级组）](tracks/open-topic/) | 大学四年级本科生及在读硕士生、博士生 | 软硬件协同与器件整体性能的发挥 | AMD FPGA / Zynq / Versal |

一支队伍只能选择一个赛道。

---

## 选定赛道之后

### RTL/HLS 本地智能体设计赛道

参考仓库按 track 分开，**两个 track 独立排名、独立评奖，推荐只选其一**：

```bash
# HLS track：产出 Vitis HLS C++
git clone https://gitee.com/Vickyiii/hlsagent2026

# RTL track：产出 Verilog / SystemVerilog
git clone https://gitee.com/Vickyiii/rtlagent2026
```

两个仓库各自包含一套能跑通的最小示范方案、示例题目、本地分级判定脚本、接口契约与
评分细则。详见 [tracks/rtl-hls-agent/](tracks/rtl-hls-agent/)。

### 具身智能赛道 · 自主选题赛道

这两个赛道不提供参考仓库，提交物为参赛队自行组织的工程包。要求、提交内容与评分权重
见各自的赛道说明。

---

## 本仓库的内容

```
README.md                        本文件
TRACK_GUIDE_2026.md              选题指南全文（公司介绍、竞赛平台、三个赛道、
                                 开发板获取途径、技术支持）
tracks/
  rtl-hls-agent/README.md        赛道入口：参考仓库地址与取用方式
  rtl-hls-agent/GUIDE.md         该赛道的指南正文
  embodied-ai/GUIDE.md           同上
  open-topic/GUIDE.md            同上
```

各 `tracks/*/GUIDE.md` 是 `TRACK_GUIDE_2026.md` 第三节按赛道的拆分，内容一致，
便于按赛道查阅。**如有出入，以 `TRACK_GUIDE_2026.md` 与大赛官方公告为准。**

---

## 时间节点

报名、作品设计、验证窗口、作品提交、评测窗口与决赛的具体日期**另行公告**，
以大赛官方发布为准：http://www.fpgachina.cn/

---

## 技术支持

| 渠道 | 地址 |
| --- | --- |
| AMD 赛灵思中文社区论坛 | https://forums.xilinx.com/cn |
| AMD 中国开发者平台 | https://developer.amd.com.cn/ |
| AMD 官方 Skills 仓库 | https://github.com/amd/skills |
| 赛道交流 QQ 群 | 1087309750 |
| 邮箱咨询 | fpgacamp.cn@outlook.com |
