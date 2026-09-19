本附录说明模板中模拟图片的用途和替换方式。正式论文写作时，应使用本人绘制的系统框图、实物照片、电路图、测试曲线和软件界面截图。

## 图片文件说明

| 文件名 | 用途说明 |
| --- | --- |
| `fig_system_architecture.png` | 系统总体架构图，可替换为自己的系统框图 |
| `fig_hardware_block.png` | 硬件连接关系图，可替换为原理框图或接口图 |
| `fig_software_flow.png` | 软件流程图，可替换为程序状态机或流程图 |
| `fig_ui_mockup.png` | 界面原型图，可替换为 OLED、串口屏或上位机截图 |
| `fig_test_layout.png` | 测试环境布置图，可替换为真实测试照片或示意图 |
| `fig_sensor_curve.png` | 传感器数据曲线，可替换为真实采样数据图 |
| `fig_energy_comparison.png` | 能耗对比柱状图，可替换为真实测试统计图 |
| `fig_response_time.png` | 响应时间测试图，可替换为真实响应测试结果 |

: 模板内置模拟图片说明 {#tab:demo-6}

## 图片替换方法

替换图片时，建议保持文件名不变，这样正文中的 `\includegraphics` 路径无需修改。若需要更换文件名，应同步修改正文中的图片路径。例如：

```tex {#code:demo-4 caption="图片插入代码示例"}
\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.90\textwidth]{figures/your_figure.png}
  \caption{你的图片标题}
  \label{fig:your-label}
\end{figure}
```
