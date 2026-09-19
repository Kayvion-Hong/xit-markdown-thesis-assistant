本附录给出若干关键程序片段，用于演示毕业论文中代码附录的排版方式。正式论文中应放置与本人系统一致、能够复现实验结果的核心代码，不建议粘贴全部工程文件。

## 滑动平均滤波函数

```c {#code:filter caption="滑动平均滤波函数示例"}
#define FILTER_N 8

float MovingAverage(float new_value)
{
    static float buffer[FILTER_N] = {0};
    static unsigned char index = 0;
    static unsigned char count = 0;
    float sum = 0.0f;

    buffer[index] = new_value;
    index = (index + 1) % FILTER_N;
    if (count < FILTER_N) {
        count++;
    }

    for (unsigned char i = 0; i < count; i++) {
        sum += buffer[i];
    }
    return sum / count;
}
```

## 自动照明控制逻辑

```c {#code:control caption="自动照明控制逻辑示例"}
void LightControl_Auto(float lux, unsigned char pir_state)
{
    const float LUX_THRESHOLD = 280.0f;

    if ((pir_state == 1) && (lux < LUX_THRESHOLD)) {
        Relay_Set(ON);
        PWM_SetDuty(60);   // 60% dimming output
    } else {
        Relay_Set(OFF);
        PWM_SetDuty(0);
    }
}
```

## 串口日志输出格式

```c {#code:uart caption="串口日志输出示例"}
printf("lux=%.1f,pir=%d,current=%.2f,mode=%d,state=%d\r\n",
       lux_value,
       pir_state,
       current_value,
       system_mode,
       light_state);
```
