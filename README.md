# xair-remote-full

在 `peterdikant/xair-remote` 基础上改造的 **X-Touch Mini → XR18 全量 OSC 控制桥**。
原项目只映射推子/静音/发送；本版本用配置驱动的分页引擎覆盖 X-Air 的几乎所有可写 OSC 参数，并保持双向同步（XR18 上的变化会回写 X-Touch 的 LED 环和按钮灯）。

## 硬件连接

- X-Touch Mini 用 USB 接电脑，**必须以 MC 模式启动**：插上 USB 时按住 `MC` 键，确认 MC LED 亮。
- 电脑与 XR18 在同一网络。XR18 可以是 WiFi AP 或接路由器；记下 IP，或让程序广播发现。
- 电脑只需要 USB 口和网卡，不需要 MIDI 转接线（X-Touch Mini 本身是 USB MIDI 类设备）。

## 安装运行

需要 Python 3.8+：

```
pip install -r requirements.txt
python xair-remote.py
```

如果自动发现失败：

```
python xair-remote.py 192.168.1.50
```

Windows 上若 `python-rtmidi` 安装失败，先装对应 Python 位数的预编译 wheel，或换用 32 位 Python。

## 操作方式

常用操作只需要两步：

- `B1`–`B16`：直接跳到 `CH01`–`CH16`，对应的一盏灯常亮。
- **编码器 8 = 轨道切换**：旋转它按 `CH01 → … → CH16 → AUX → FX SEND1 → FX SEND4` 顺序切换，到两端停止；**AUX / FX 只能通过它到达**。LED 环显示当前轨道位置；按下它把当前页存为收藏。切换时向 X-Air Edit 发送**左右方向键**，让界面选中框跟着走，且永远不会越过 FX4 进入 BUS / LR。
- 编码器 1–7：控制当前轨道的固定快捷参数，无需翻页。
- `LA` / `LB`：切换层，两层始终跟随同一个轨道（B1–B16 或旋钮 8 切轨道时两层同步）。
- 主推子固定控制 Main LR 音量。

**Layer A 旋钮 1–7**（CH 快捷页）：

| 旋钮 | 参数 |
|---|---|
| 1 | Fader |
| 2 | Gain（步进 0.04） |
| 3 | EQ High |
| 4 | EQ Mid |
| 5 | EQ Mid Freq |
| 6 | EQ Low |
| 7 | Pan |
| 8 | 轨道切换（按下 = 存收藏） |

**Layer B 旋钮 1–7**（跟随当前轨道）：

| 旋钮 | 参数 |
|---|---|
| 1 | Noise Gate Threshold |
| 2 | Compressor Threshold |
| 3 | FX Send 1 → `/mix/07/level` |
| 4 | FX Send 2 → `/mix/08/level` |
| 5 | FX Send 3 → `/mix/09/level` |
| 6 | FX Send 4 → `/mix/10/level` |
| 7 | AUX Send 1 + 2（同时写 `/mix/01/level` 与 `/mix/02/level`） |

X-Air 里 FX1–4 是 mixbus 7–10，AUX/BUS send 1–6 才是 `/mix/01..06/level`，不要混淆。

**两层通用的旋钮按下功能**（对当前轨道，启动时会在控制台打印带 OSC 地址的完整表）：

| 按下旋钮 | 功能 | OSC 地址（CH NN） |
|---|---|---|
| 1 | Mute | `/ch/NN/mix/on` |
| 2 | Solo | `/-stat/solosw/NN`（X-Air 的 solo 开关状态地址） |
| 3 | Polarity（相位反转） | `/ch/NN/preamp/invert` |
| 4 | Noise Gate ON/OFF | `/ch/NN/gate/on` |
| 5 | EQ ON/OFF | `/ch/NN/eq/on` |
| 6 | Compressor ON/OFF | `/ch/NN/dyn/on` |
| 7 | 48V phantom | `/headamp/NN/phantom` |

环灯逻辑（**已反转**）：功能处于 **ON** 状态时，该旋钮环 **常亮显示当前数值**；处于 **OFF** 状态时，环灯 **每 5 秒爆闪 2 下**（60ms 亮/60ms 灭）提示它已关闭，结束后恢复数值显示。X-Touch Mini 环灯没有亮度寄存器，无法做真正的渐变呼吸。手动转动某个旋钮时，会临时（约 0.4 秒）优先显示数值圈。切换轨道或启动时会主动查询 XR18 上全部 7 个开关地址，逐条同步状态。

Pan（Layer A 旋钮 7）未收到 XR18 反馈时默认居中，旋钮环使用 Pan 模式（17=全左，22=居中，27=全右）：向左拧左边灯增多，向右拧右边灯增多。旋钮 8 使用单点灯光指示当前轨道位置，1–7 使用填充式数值灯圈。

按钮翻页、Shift、Tap、Home 已取消。

X-Air Edit 选中框只在上述 21 个轨道内跟随；启动时读取一次选中位置作校准，之后只用于防止焦点越界，不会反向抢改桥内部轨道。若在 X-Air Edit 里手动点了别的轨道，用 B1–B16 或旋钮 8 回到桥的轨道即可。X-Air Edit 窗口需保持打开且未被最小化。

### 按钮灯（当前选中轨道）

- **CH01–CH16**：B1–B16 中**只有一盏灯常亮**，对应当前通道。
- **AUX**：**B1 爆闪**；**FX SEND1–4**：**B2–B5** 对应一盏**爆闪**。
- AUX / FX 只能用旋钮 8 到达，按钮不再直跳；翻页 / Shift / Tap / Home 已取消。

轨道范围固定为 `CH01 → … → CH16 → AUX → FX SEND1 → FX SEND4`，到两端停止，不再循环回绕。

终端会打印当前所在层和页面名称。

## 标签

```
python tools/gen_labels.py
```

生成 `labels.html`，用浏览器打开并打印（100% 比例），按层/组列出每一页的 8 个旋钮含义。

## 全量的边界

- 8 个编码器同时只能呈现 8 个参数，因此采用 403 页分页；实际使用建议把常用页设为收藏。
- 字符串类参数（通道名、文件名等）没有做旋钮编辑；枚举/整数/浮点参数均可控。
- FX 参数按 `/fx/<槽>/par/01..64` 通用生成，标签是 `PAR n`；具体效果器的参数名需按官方 `parameters.txt` 在 `lib/params.py` 中自行改名。
- 参数表基于 X-Air 1.14 协议文档；新固件的个别地址若有变化，改 `lib/params.py` 即可。
- 多个控制端同时写同一参数可能互相覆盖；X-Air Edit 可以开着当显示器，但尽量只用一个写入端。

## 代码结构

- `lib/params.py`：参数与分页定义（改动最多）
- `lib/mixerstate.py`：状态缓存、分页导航、OSC↔MIDI 转换
- `lib/midicontroller.py`：X-Touch Mini MC 模式 MIDI 收发
- `lib/xair.py`：OSC/UDP 客户端与状态广播订阅
- `xair-remote.py`：入口

基于 MIT 协议的上游项目 fork，保留原协议实现思路，控制映射部分为新增实现。
