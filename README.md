# X518 力传感器 Python 接口

给蛇形机器人控制程序直接调用的 Python 包。硬件链路为一维传感器 → X518 → USB-RS485 → 主机；一次读两通道。原来的 CLI、上位机、手册及实验数据均保留在父目录，新包不依赖父目录路径。

这是进程内 Python API。同门将 USB-RS485 接到自己的 Mac 后可以直接调用；若采集器仍接在你的 Windows 电脑上，这个包不能跨网络读它，需要另行设计服务端和客户端。

## 环境与快速运行

暂定 Python 3.12，声明兼容范围 3.10–3.14；唯一运行依赖沿用 pyserial 3.5。开发机 uv 为 0.10.10，CI 固定此版本。与同门一样使用 Hatchling 构建，本包固定为 1.27.0（满足他的 `>=1.27.0`），另有可编辑安装所需的 editables 0.5；两者同时列入 dev 组，便于在项目环境内构建。`uv.lock` 锁定运行和开发依赖。

**已对齐的配置与待确认项**：2026-10-06，GitHub 插件读取失败，公开 GitHub API 返回 404；随后用户提供同门项目的 pyproject.toml：名称 `xh430-pure-python-control`，Python `>=3.10`，Hatchling `>=1.27.0`，依赖 dynamixel-sdk、PyYAML、pyserial `>=3.5`，可选 GUI 依赖 matplotlib/PyQt5。此包不需要舵机和 GUI 依赖，其 pyserial 3.5 满足同门约束，uv 合并项目依赖时仍需整体解析。尚缺他的 `.python-version`、`uv --version`、实际 lock；不能声称精确版本已一致。若他使用 3.10–3.14，可将这里的 `.python-version` 改成相同版本，重新验证。若超出该范围，先验证再改支持范围。

已安装 uv 的前提下，在本目录执行；以下命令通用于 PowerShell 和 macOS 终端，无需手工激活环境：

```text
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m x518_force --demo --count 3
uv run --locked python -m x518_force --list-ports
```

`uv sync` 安装到本项目 `.venv`，不共享或复制 Windows 虚拟环境到 Mac。迁移时复制源代码、pyproject、lock 和版本文件，目标主机重新同步。[uv 锁定与同步说明](https://docs.astral.sh/uv/concepts/projects/sync/)

硬件示例（端口是占位示例，先列出实际端口）：

```text
# Windows
uv run --locked python -m x518_force --port COM3 --decimals 2 --unit kg --count 20
# macOS
uv run --locked python -m x518_force --port /dev/cu.usbserial-实际编号 --decimals 2 --unit kg --count 20
```

Mac 使用实际 `/dev/cu.*` 端口；USB 转换器可能需要厂商的 macOS 驱动，取决于芯片型号。pyserial 支持 Windows、Linux 和 macOS，但这不能替代你的转换器实测。[pyserial 平台说明](https://pyserial.readthedocs.io/en/latest/pyserial.html)

## 同门如何调用

将整个本目录交给同门，例如放在他的机器人仓库旁，命名为 `x518_force_api`。在**他的机器人项目目录**运行：

```text
uv add --editable ../x518_force_api
uv run python -c "from x518_force import Config, X518Sensor; print('import OK')"
```

这是同门修改自己项目依赖的操作，不在本次工作中执行。`uv add` 会更新他的 pyproject 和 lock；以后共享时相对路径应保持一致。稳定交付可运行 `uv build`，把 `dist/` 中的 `.whl` 交给他，再在他的项目里 `uv add /实际路径/x518_force-0.1.0-py3-none-any.whl`，避免源代码相对路径依赖。若以后使用 Git 依赖，应固定具体 commit；本仓库远程地址为 https://github.com/AAA0error/x518-force-api.git。[uv 依赖管理](https://docs.astral.sh/uv/concepts/projects/dependencies/)

机器人代码只需：

```python
from x518_force import Config, X518Sensor, ProtocolError, SensorError

config = Config(port="/dev/cu.usbserial-实际编号", decimals=2, unit="kg")
try:
    with X518Sensor(config) as sensor:
        sample = sensor.read()
        ch1, ch2 = sample.values
        print(sample.raw, ch1, ch2, sample.unit, sample.timestamp)
except (ProtocolError, SensorError) as exc:
    # 在控制器中实现明确的安全处理；不要将错误当成零力。
    print("力值无效:", exc)
```

离线联调：`with X518Sensor(Config(), demo=True) as sensor:`，其他调用不变。首帧 raw 为 `(101, -51)`，每次变化；`source="demo"`，这些合成值不能用于真实力反馈。

| 接口/字段 | 含义 |
| --- | --- |
| `Config(...)` | 不可变配置，构造时验证参数；默认 115200、8N1、slave=1、timeout=1、decimals=2、unit=kg |
| `X518Sensor(config)` | 构造时不打开串口；`open()` 或 `with` 才打开 |
| `read()` | 发起一笔 FC03 事务，返回新的不可变 `Sample` 或抛出异常 |
| `sample.raw` | `(CH1, CH2)` 有符号 int32 原始整数 |
| `sample.values` | `raw / 10**decimals`，不是自动校准的牛顿数 |
| `sample.unit / decimals` | 调用者提供的显示标签、小数位；没有自动读取设备配置 |
| `timestamp` | 主机接收完成后的 UTC 时间字符串，不是设备内部采样时刻 |
| `request_started_s / monotonic_s` | 主机请求开始/接收完成的单调时钟，不能跨电脑比较 |
| `age_s()` | 距主机接收完成的秒数，不包含设备滤波/采样滞后 |
| `source / tx / rx` | serial 或 demo；原始请求、响应 bytes |
| `ProtocolError` | 超时空帧、短帧、CRC/地址/功能码错误等；设备异常子类 `ModbusException.code` 可读取 |
| `SensorError` | 未打开、串口占用/断开、短写等；底层串口异常保留为 cause |
| `close()` | 释放串口，可重复调用；`with` 在异常退出时也关闭 |
| `list_ports()` | 返回 pyserial 端口描述对象列表，不探测从站或自动选设备 |

`read()` **会阻塞**。响应接收共用一个 timeout 截止时间，写入另有 write_timeout，因此整笔事务可能接近两倍 timeout 加帧间隔/系统调度；USB驱动的阻塞行为仍需实测。此包没有硬实时保证。5 Hz 入门采集与高频关节控制应分开：在采集线程中独占一个 Sensor，通过有界队列交给控制线程；控制器检查接收年龄、错误状态及超时，禁止无限等待或把上次值当新测量。线程锁防止同一对象的读取/关闭相互打断，但不能协调多个对象或其他进程打开同一串口。

## 协议与力值边界

参考父目录的原厂 PDF 第 7、12、13 页，及已有 README_X518、协议/读取/上位机脚本。仅发送 FC03，从 `0x0A00` 读 4 个 16-bit 寄存器；不清零、不标定、不写设备设置。原协议与分段接收函数分别复制到 `protocol.py` 和 `transport.py`，保持已有行为。

默认正确请求是 `01 03 0A 00 00 04 47 D1`。手册和任务书中的 `46 D1` 是 CRC 笔误；已用标准 CRC 和完整帧余数验证。示例响应 `01 03 08 00 00 00 06 FF FF 67 4B 77 F4` 解码为 `(6, -39093)`。支持高字在前和 `word_swap=True`。

默认 `raw/100`、kg 只是沿用已有项目配置假设；手册出厂单位是 N，实际设备未必相同。改 `unit="N"` **只改标签**，不换算读数。使用反馈前须与原厂显示、空载和已知载荷对照，确认两通道映射、方向、单位、小数位及标定。负数不是通信失败的充分证据。一次读取两路减少通信时差，但不证明设备同时采样。

## 没有 Mac，如何验证

本目录 `.github/workflows/compatibility.yml` 已配置 Windows、Linux、macOS Apple Silicon（`macos-15`）、macOS Intel（`macos-15-intel`），分别运行 Python 3.10/3.12/3.14。它验证 uv 安装、测试、演示、构建，以及在源码目录外安装 wheel 后调用；共 12 组任务。[GitHub 官方 runner 说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

1. 仓库地址：[AAA0error/x518-force-api](https://github.com/AAA0error/x518-force-api)。Actions 运行结果以 GitHub 页面为准。
2. 源码更新提交并推送后会触发测试；应包含隐藏的 `.github` 和 `uv.lock`，不上传 `.venv` 或本地实验数据。
3. 在 Actions 查看 `Python platform compatibility`；可用 Run workflow 手动触发，保留日志、Python/uv版本、runner架构和 commit。
4. 只有 Mac 两种架构对应的任务通过，才可以说这些软件测试在 macOS 上通过；现在仍是待执行。

公开仓库标准 runner 通常免费；私有仓库受免费分钟额度/计费规则约束，运行前查看自己的额度。Windows 上的 Docker/WSL 是 Linux 环境，不能充当 macOS 验证。[GitHub runner 资源与费用说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

云端 runner 不能访问你桌上的 USB-RS485，所以最终需要同门做以下 Mac 验收：记录 Mac/CPU/Python/uv/转换器芯片与驱动版本；列出实际端口；关闭其他串口工具；用确认过的参数连续读取；对照已知载荷与原厂读数；测试拔线报错、退出后端口释放、重新连接；测量实际读数间隔和延迟。软件测试通过并不证明硬件驱动、标定或控制稳定性。

## 文件与本次验证

- `x518_force/sensor.py`、`__init__.py`：公开接口、配置、样本、串口生命周期、合成演示。
- `x518_force/protocol.py`、`transport.py`：从既有实现复制的严格协议校验与分段接收。
- `x518_force/__main__.py`、`examples/read_force.py`：跨平台命令行/演示入口。
- `pyproject.toml`、`.python-version`、`uv.lock`、`.gitignore`：包安装、版本与环境管理。
- `tests/test_sensor.py`：协议错误、边界值、字序、分段接收、资源关闭与API/CLI测试。
- `.github/workflows/compatibility.yml`：待在 GitHub 执行的跨平台验证。

本地已在 Windows / Python 3.12.4 / uv 0.10.10 下完成以下验证：

- 使用原有环境通过 11 个离线测试、CLI 合成演示和 compileall。
- 经用户授权，仅在本项目 `.venv` 安装运行/构建依赖；`uv sync --locked --no-build-isolation --python 3.12 --no-python-downloads` 成功。
- 在 uv 项目环境再次通过 11 个测试和 `examples/read_force.py --demo`。
- `uv build --no-build-isolation --no-sources` 成功构建 sdist 和 wheel。
- 将 wheel 安装到同一 `.venv`，在源码目录之外验证导入路径确实来自 site-packages，调用返回 `(101, -51)`，并再次通过全部 11 个测试；随后恢复开发用可编辑安装。
- `uv lock --check --offline --python 3.12 --no-python-downloads` 通过。

本地构建采用预装开发依赖的方式，避免在 `.venv` 之外建立临时构建环境；Hatchling 的可编辑安装需要 editables，已显式声明以修复初次缺少该构建依赖的失败。普通目标主机可使用上面的 `uv sync --locked` 自动构建；CI 会验证这一标准流程。

未打开真实串口；macOS、Linux 和其他 Python 版本运行尚未验证。项目未配置独立 lint/typecheck 工具。云端测试全部待执行，不把准备好测试等同于测试通过。

已有环境也可直接在本目录 `python -m unittest discover -s tests -v`、`python -m x518_force --demo --count 3`；这验证源码运行，不能代替包安装验证。
