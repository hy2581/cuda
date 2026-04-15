# Arm Ethos-U NPU（手动翻译）

> 原始页面：`https://developer.arm.com/documentation/109267/0103/Arm-Ethos-U-NPU`

机器学习（ML）应用中的大多数工作负载都要执行神经网络（NN）推理。虽然在通用处理器上运行的软件也能执行 NN 推理，但使用硬件加速器可以显著提升性能。使用硬件加速器执行 NN 推理通常还能提升能效，并释放处理器带宽去处理其他任务。

NN 推理硬件加速器有很多类型。例如，Arm Ethos-U 是面向微控制器和片上系统（SoC）设计的一类硬件加速器家族，这类加速器被称为神经处理单元（NPU）。

Ethos-U NPU 体积小、功耗低，能够降低运行 ML 神经网络所需的推理时间和内存需求。Ethos-U 家族包括以下设计：

- Ethos-U55  
- Ethos-U65  
- Ethos-U85

这些 NPU 已经用于商用产品。例如：

- Ethos-U55 用于：
  - Alif Semiconductor 的 Alif Ensemble 系列；
  - Infineon 的 PSoC Edge；
  - Himax Technologies 的 WiseEye2 AL Processor（并有 Seeed Studio 的低成本开发板）。
- Ethos-U65 用于 NXP 的 i.MX 93 系列。

你也可以在不使用真实硬件的情况下评估 Ethos-U55/U65。例如，可以使用仿真环境，如 Arm Virtual Hardware（AVH）或 Fixed Virtual Platform（FVP）。这些工具的更多信息见文档 *Tool support for the Arm Ethos-U NPU*。

Ethos-U85 是 Ethos-U 产品家族中的最新成员。它最高可提供 2048 个 MAC 单元，并支持包括 Transformer 网络在内的广泛 NN 模型。同时，其能效最多可比此前的 Ethos-U 设计提升 20%。Ethos-U85 继承了前代方案并提供一致的工具链，因此开发者可以复用此前在 Arm ML 软件上的投入。关于 Ethos-U85 的更多技术细节将在今年稍后发布。本文档其余内容主要聚焦 Ethos-U55 与 Ethos-U65。
