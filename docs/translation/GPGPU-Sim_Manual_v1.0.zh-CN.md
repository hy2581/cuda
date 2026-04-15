# GPGPU-Sim 手册（v1.0）中文人工译稿

> 说明：本文件基于官方文档 **GPGPU-Sim Manual, Version 1.0**（对应 GPGPU-Sim 2.1.1b）进行人工翻译整理。  
> 原文下载文件：`docs/original/GPGPU-Sim_Manual_v1.0.html`  
> 原始链接：<https://pages.cs.wisc.edu/~chen-han/doc/GPGPU-Sim_Manual.html>

---

## 1. 作者与版本

- 作者：Wilson W. L. Fung、Ali Bakhoda、Tor M. Aamodt  
- 本手册版本：1.0  
- 对应模拟器版本：GPGPU-Sim 2.1.1b

## 2. 简介

本文档介绍 GPGPU-Sim：一个面向众核加速器（如 GPU）的**周期级精确性能模拟器**。  
手册目标是指导用户完成 CUDA/OpenCL 程序在 GPGPU-Sim 上的搭建与运行，并说明如何扩展模拟器，主要包括：

- 模拟配置项的说明
- 模拟输出统计指标的解释
- 软件架构概览（便于二次开发）

原文也强调：本手册并非穷尽式参考，若文档无法覆盖你的问题，建议到 gpgpu-sim.org 相关社区继续讨论。

### 2.1 版权与引用

该版本仅用于非商业用途，版权信息见发布包中的 `COPYRIGHT` 文件。  
若在研究中使用 GPGPU-Sim，请引用 ISPASS 2009 论文：

Ali Bakhoda, George Yuan, Wilson W. L. Fung, Henry Wong, Tor M. Aamodt,  
Analyzing CUDA Workloads Using a Detailed GPU Simulator, ISPASS 2009.

### 2.2 项目历史与贡献

- GPGPU-Sim 由 UBC 团队发起，后续有多位研究者贡献。  
- AerialVision 可视化工具在 2.1.1b 中发布。  
- 早期版本曾使用 SimpleScalar 的部分功能代码；在 2.1.1b 中已经移除。  
- 为与真实 CUDA 程序输出兼容，部分 PTX 指令通过 CUDA Math 库实现。

## 3. 系统需求

- 模拟器本身不要求物理 GPU。  
- 需要安装 CUDA Toolkit。  
- 若使用 OpenCL，通常还需要 NVIDIA OpenCL 驱动（很多场景下依赖物理 GPU）。

## 4. 功能与 CUDA 版本支持

### 4.1 GPGPU-Sim 2.1.1b（本手册对应）

主要特性（节选）：

- 支持 CUDA 2.3（及更早）/ PTX 1.4
- 新增 OpenCL 支持（依赖 NVIDIA OpenCL 驱动）
- 新增性能可视化工具（AerialVision）
- 改进共享内存 bank conflict 建模
- 增加 Quadro FX5800 配置
- 增加互连集中度（concentration）建模以近似 TPC 效应
- 支持同一 GPU 的 GPU-to-GPU 内存拷贝（仅功能支持，不建模延迟）

### 4.2 其他版本简述

- 2.1.0b：支持 CUDA 2.2（及更早）  
- 2.0：支持 CUDA 1.1（及更早）

### 4.3 AerialVision 性能可视化器

2.1.1b 内置 Python 可视化工具，有助于定位硬件/软件瓶颈。详见 `doc` 目录中相关说明。

### 4.4 内存拷贝支持

`cudaMemcpy()` 的 H2D / D2H / D2D 功能可用，但默认**不模拟这些操作的时间开销**。

### 4.5 多 GPU

该版本不支持同时模拟多个 GPU。

## 5. 构建 GPGPU-Sim

### 5.1 软件依赖

- GCC 4.0+  
- CUDA 2.x 推荐 GCC 4.3  
- CUDA 1.1 推荐 GCC 4.1

### 5.2 已测试平台（原文示例）

- Ubuntu 8.10 / 9.04（社区测试）
- Mac OS X、Cygwin 在当时存在适配问题

### 5.3 编译前环境变量（核心）

需要设置（原文步骤 4）：

- `GPGPUSIM_ROOT`：GPGPU-Sim 根目录
- `CUDAHOME`：CUDA 安装目录
- `NVIDIA_CUDA_SDK_LOCATION`：CUDA SDK 目录
- 将 `$CUDAHOME/bin` 与 `$GPGPUSIM_ROOT/bin` 加入 `PATH`
- 将 `$GPGPUSIM_ROOT/lib` 加入 `LD_LIBRARY_PATH`，并从中移除 CUDA 原生运行库路径（避免链接到真实驱动库）
- OpenCL 场景设置 `NVOPENCL_LIBDIR`

### 5.4 编译产物说明

动态链接场景：

- `lib/libcudart.so`（CUDA）
- `lib/libOpenCL.so`（OpenCL）

静态链接场景常见库：

- `src/libgpgpusim.a`
- `src/cuda-sim/libgpgpu_ptx_sim.a`
- `src/intersim/libintersim.a`
- `lib/libcuda.a`

## 6. 将应用迁移到 GPGPU-Sim

GPGPU-Sim 通过模拟 CUDA/OpenCL API 库接管程序执行：

- 可静态链接 `libcuda.a`
- 可动态链接 `libcudart.so` / `libOpenCL.so`

并且运行目录需准备：

- `gpgpusim.config`
- 互连配置文件（由 `-inter_config_file` 指定）

### 6.1 动态链接方式（推荐）

适用于 CUDA 2.1+ 预编译程序，关键做法是将 `<GPGPU-Sim>/lib` 放到 `LD_LIBRARY_PATH` 前面，再执行应用并用 `ldd` 验证链接目标。

### 6.2 静态链接方式

可继续沿用 `common/common.mk` 风格，也可手动改构建系统，添加 `nvcc` 编译选项与 g++ 链接参数（原文给出了完整示例）。

### 6.3 OpenCL 应用迁移

需在编译前正确设置 `NVOPENCL_LIBDIR`，并确保链接链路指向 NVIDIA 提供的 OpenCL 库目录。

## 7. 常见编译错误（手册要点）

1. **CUDAHOME 指错**：路径层级缺少末尾 `cuda/` 目录。  
2. **找不到 `-lcutil`**：`NVIDIA_CUDA_SDK_LOCATION` 不正确，或未先构建 `libcutil.a`。  
3. **OpenCL 递归错误**：`NVOPENCL_LIBDIR` 误指向 GPGPU-Sim 自己构建的 `libOpenCL.so`。

## 8. 运行 GPGPU-Sim

- 程序成功迁移后，执行应用会触发 GPGPU-Sim，而非真实 CUDA 驱动。  
- 默认使用二进制内嵌 PTX。若要使用当前目录 PTX，设置：

```bash
export PTX_SIM_USE_PTX_FILE=1
```

补充：

- OpenCL 要求 PTX 文件按 `_n.ptx` 命名（按 `clBuildProgram` 调用顺序编号）。  
- 如手工生成 `.ptx`，建议对每个 PTX 跑 `scripts/gen_ptxinfo` 生成 `.ptxinfo`，用于告知寄存器等资源需求。  
- 启动时会自动读取当前目录 `gpgpusim.config`。

## 9. 微架构模型（摘要）

本节对应 ISPASS 2009 论文中的模型，并在 2.1.1b 增加：

- GPU concentration（多 shader core 共享一个互连端口）
- 更细粒度共享内存 bank conflict 检查（16-thread 分组）

## 10. 配置选项（中文说明摘译）

手册将选项分为：仿真运行、统计采集、着色器核心流水线、缓存/共享内存、DRAM 控制器、互连网络等类别。  
下面给出高频参数的中文释义（完整参数表请对照原文）：

- `-gpgpu_max_cycle`：最大仿真周期，超限提前停止  
- `-gpgpu_max_insn`：最大指令数，超限提前停止  
- `-gpgpu_ptx_sim_mode`：0 性能仿真，1 功能仿真  
- `-gpgpu_deadlock_detect`：是否启用死锁检测  
- `-visualizer_enabled`：是否输出可视化日志  
- `-gpgpu_n_shader`：shader core 数量  
- `-gpgpu_n_mem`：内存控制器（DRAM 通道）数量  
- `-gpgpu_clock_domains`：核心/互连/L2/DRAM 时钟域频率  
- `-gpgpu_no_dl1`：关闭 L1 data cache  
- `-gpgpu_cache:dl1`：L1 数据缓存结构参数  
- `-gpgpu_cache:dl2`：L2 缓存结构参数  
- `-gpgpu_shmem_size`：每个 core 的共享内存大小  
- `-gpgpu_shmem_bkconflict`：共享内存 bank conflict 建模开关  
- `-gpgpu_dram_scheduler`：DRAM 调度策略（如 fifo / fr-fcfs）  
- `-inter_config_file`：互连网络配置文件路径  
- `-gpu_concentration`：每个互连端口共享的 shader core 数

### 10.1 拓扑配置说明

默认 mesh 拓扑会限制“核心数与内存通道数”的可组合关系。  
如果你要更自由地调整规模，可以：

- 改 mesh 尺寸（并同步映射），或  
- 使用 `fly` 拓扑（近似交叉开关）以减少映射约束。

### 10.2 时钟域说明

手册解释了如何将 NVIDIA 规格里的 shader clock 映射到模拟器 core clock，并给出了“按流水线宽度比例缩放频率”的建模理由。

### 10.3 共享内存 bank conflict

2.1.1b 按每 warp 两组（每组 16 线程）检查 bank conflict，更贴近 G80/GT200 行为。

## 11. 理解模拟输出（摘要）

每次 kernel 结束后会输出统计信息。重点指标包括：

- `gpu_sim_cycle`：该 kernel 执行所需 core 周期  
- `gpu_sim_insn`：执行指令数  
- `gpu_ipc`：吞吐指标（指令/周期）  
- 多类存储层级统计（访问量、命中/未命中、延迟）
- 控制流统计（分支/发散相关）
- DRAM、缓存与互连统计

这些指标可用于瓶颈分析，例如判断是算力受限、L1/L2/DRAM 受限还是互连受限。

## 12. 扩展与二次开发指引（摘要）

原文“Extension/Hacking Guideline”介绍了各模块职责边界，包括：

- 核心模拟模块
- 工具与辅助组件
- CUDA/OpenCL 接口层
- InterSim（源于 Booksim 的互连模拟）

可作为阅读源码与扩展实验功能的入口。

---

## 译者备注

1. 本中文稿以“可实操”为目标，对原文做了人工精简与结构化转述。  
2. 参数细节与全部统计项请以原始 HTML 手册为准。  
3. 若你希望，我可以继续在此基础上做“逐段逐句对照版”（英文原句 + 中文逐句译文）的完整版。
