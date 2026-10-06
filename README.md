# X518 力传感器 Python API — 第一版（0.1.0）

面向 Windows 与 macOS 的只读 Python 接口，用于蛇形机器人获取 X518 测量值。默认一次读取 CH1、CH2，也支持只读 CH1。硬件连接：传感器 → X518 → USB-RS485 → 运行 Python 的电脑。

这是进程内 API；传感器须连接到运行代码的电脑。接口不提供清零、标定、修改设备参数或跨电脑网络读取。

## 1. 获取文件

### 压缩包方式

解压 `x518_force_api_v0.1.0.zip`，得到 `x518_force_api` 文件夹。建议把它放在机器人项目旁：

```text
工作目录/
├── Snake_Robot_XH430/
└── x518_force_api/
```

ZIP 不包含 Git 历史、虚拟环境、临时测速脚本或实验数据。更新时重新接收压缩包，保留自己的代码和数据。

### GitHub 方式

首次在工作目录执行：

```bash
git clone https://github.com/AAA0error/x518-force-api.git x518_force_api
cd x518_force_api
```

需要固定第一版时执行 `git checkout v0.1.0`。要在 main 上接收后续更新，执行：

```bash
git switch main
git pull --ff-only
uv sync --locked
```

如果有本地修改或分支分歧，先用 `git status` 检查并保留自己的修改，不要强制覆盖。记录实验软件版本可用 `git rev-parse HEAD`。

## 2. 安装与离线检查

前提：已安装 uv；GitHub 方式还需要 Git。首次同步需要联网下载 Python 和依赖。在接口项目目录执行，命令可用于 Windows PowerShell 或 Mac 终端：

```bash
uv --version
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m x518_force --demo --count 3
```

预期：18 个测试通过并显示 `OK`。演示首条 raw 为 `[101, -51]`，来源为 `demo`；不打开真实串口。

项目默认 Python 3.12，兼容范围 `>=3.10,<3.15`，运行依赖固定 pyserial 3.5；构建使用 Hatchling 1.27.0。uv 开发/CI 版本为 0.10.10。`uv.lock` 固定依赖，环境建在本项目 `.venv`。不要复制 Windows 的虚拟环境到 Mac，目标电脑重新执行同步即可。

同门机器人项目的 Python `>=3.10`、pyserial 3.5 和 Hatchling 构建方式已核对；具体 Python/uv 版本未确认。机器人运行环境也必须满足本包的 Python 范围。独立项目使用 3.12 不会强制机器人项目改成 3.12。

## 3. 加入机器人程序

上面的安装只服务于接口项目本身。机器人程序要能导入这个包，还需在**机器人项目目录**执行：

```bash
cd "/实际工作目录/Snake_Robot_XH430"
uv add --editable ../x518_force_api
uv run python -c "from x518_force import Config, X518Sensor; print('import OK')"
```

预期输出 `import OK`。这会更新机器人项目的 pyproject 和 lock；不要用接口项目的 uv.lock 覆盖机器人项目的锁文件。保持两个项目的相对路径。源码更新会直接反映到可编辑安装；若依赖有变化，在机器人项目执行 `uv sync`。

也可安装交付的 wheel：在机器人项目执行 `uv add /实际路径/x518_force-0.1.0-py3-none-any.whl`，不依赖接口源码的相对路径。

## 4. 接硬件测试

关闭上位机、Modbus Poll 和其他占用串口的程序。在接口项目目录列出实际端口：

```bash
uv run --locked python -m x518_force --list-ports
```

Windows 示例（COM3 需替换为实际端口）：

```powershell
uv run --locked python -m x518_force --port COM3 --baud 115200 --slave 1 --decimals 2 --unit kg --interval 0.2 --count 100
```

Mac 示例（`/dev/cu.*` 为实际 USB 串口；不要原样使用占位符）：

```bash
uv run --locked python -m x518_force --port /dev/cu.usbserial-实际编号 --baud 115200 --slave 1 --decimals 2 --unit kg --interval 0.2 --count 100
```

真实数据来源标记为 `serial`。依次空载、加载已知重物、卸载、重复加载，核对通道、方向和重复性；退出后再次读取，确认端口已释放。Mac 的 USB 转换器驱动是否适用需在实际机器验证。

`--unit kg` 只是标签；必须核对设备真实单位和小数位。通信正常不代表标定正确。

## 5. Python 调用

双通道（默认）：

```python
from x518_force import Config, X518Sensor, ProtocolError, SensorError

config = Config(port="/dev/cu.usbserial-实际编号", decimals=2, unit="kg")
try:
    with X518Sensor(config) as sensor:
        sample = sensor.read()
        ch1, ch2 = sample.values
        print(sample.raw, ch1, ch2, sample.unit, sample.timestamp)
except (ProtocolError, SensorError) as exc:
    # 控制器应明确处理无效力值；不要将异常当成零力。
    print("力值无效:", exc)
```

只读 CH1（Python API）：

```python
with X518Sensor(Config(port="COM3", channels=1)) as sensor:
    sample = sensor.read()
    ch1_raw = sample.raw[0]
    ch1 = sample.values[0]
```

离线联调用 `X518Sensor(Config(), demo=True)`；单通道可用 `Config(channels=1)`。演示是合成数据，不可用于真实力反馈。

| 接口或字段 | 含义 |
| --- | --- |
| `Config(...)` | 不可变配置；默认 115200、8N1、slave=1、timeout=1、decimals=2、unit=kg、channels=2 |
| `open()` / `with` | 打开设备；仅构造对象不会打开串口 |
| `read()` | 一笔新的读取事务，成功返回 Sample，失败抛异常 |
| `sample.raw` | 有符号 int32 元组；单通道长度 1，双通道长度 2 |
| `sample.values` | `raw / 10**decimals`，不是自动校准的牛顿数 |
| `unit / decimals` | 调用者提供的标签和缩放配置，未自动读取设备设置 |
| `timestamp` | 主机接收完成的 UTC 时间，不是设备内部采样时间 |
| `request_started_s / monotonic_s` | 主机请求开始／接收完成的单调时钟，不可跨电脑比较 |
| `age_s()` | 距主机接收完成的秒数，不包含设备滤波滞后 |
| `source / tx / rx` | serial 或 demo；原始请求／响应 bytes |
| `ProtocolError` | 空帧、短帧、CRC、地址、功能码错误等；设备异常为 ModbusException，可读取 code |
| `SensorError` | 串口打不开、断线、短写或对象未打开等 |
| `close()` | 释放串口，可重复调用；with 在异常退出时也关闭 |
| `list_ports()` | 枚举端口，不自动选设备或探测从站 |

`read()` 会阻塞，响应使用一个 timeout 截止时间，写入另有 write_timeout。不要放在需要严格周期的高频关节控制循环中；建议采集线程独占 Sensor，通过有界队列交给控制线程，并检查数据年龄和错误状态。线程锁只协调同一个 Sensor 对象，不协调其他对象或程序。

## 6. 协议、性能与验证边界

仅使用 Modbus RTU FC03，固定从 0x0A00 读取测量值：CH1 读 2 个寄存器，CH1+CH2 读 4 个。支持高字在前及 `word_swap=True`。严格检查长度、byte count、slave、功能码及 CRC；错误不返回零值或缓存测量。

正确双通道默认请求为 `01 03 0A 00 00 04 47 D1`。原厂手册印刷的 `46 D1` 是 CRC 笔误。示例响应 `01 03 08 00 00 00 06 FF FF 67 4B 77 F4` 解析为 `(6, -39093)`。

配置 `unit="N"` 只改标签，不做单位转换。投入反馈前应核对两通道映射、方向、单位、小数位和标定。一次读取两通道不证明设备同时采样。

Windows / CH340 / 115200 的短时硬件测试中，双通道约 62 Hz、平均约 16 ms，单通道约 64 Hz；这些是特定链路的观测，不是性能保证或设备独立采样率。设备内部 1600 Hz 采样设置不代表电脑可取得 1600 次新测量。第一版不承诺微秒级或硬实时读取。

`.github/workflows/compatibility.yml` 在 Windows、Mac Apple Silicon、Mac Intel 上测试 Python 3.10/3.12/3.14，共 9 组；执行安装、18 个离线测试、演示、构建及脱离源码的 wheel 调用。最新结果见 [GitHub Actions](https://github.com/AAA0error/x518-force-api/actions)。云端无法访问桌上的 USB 设备，不能替代 Mac 真实串口、标定或机器人控制验收。

## 7. 第一版文件

- `x518_force/`：公开 API、串口生命周期、协议、接收和命令行入口。
- `examples/read_force.py`：正式调用示例。
- `tests/test_sensor.py`、`tests/test_transport.py`：协议、单／双通道、异常和接收截止时间回归测试。
- `pyproject.toml`、`uv.lock`、`.python-version`：包与环境管理。
- `.github/workflows/compatibility.yml`：跨平台验证。
- `README.md`：接收、安装、调用和硬件验收说明。

临时测速脚本、诊断脚本和数据已从第一版交付目录移除。第一版版本号为 0.1.0，Git 标记为 v0.1.0。
