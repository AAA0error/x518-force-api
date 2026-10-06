# X518 力传感器 Python 接口

给蛇形机器人控制程序直接调用的 Python 包。硬件链路为一维传感器 → X518 → USB-RS485 → 主机；一次读两通道。交付包不依赖原开发目录，无需原上位机、实验 CSV 或 Windows 虚拟环境。当前交付对象为 Windows 与 macOS。

这是进程内 Python API。同门将 USB-RS485 接到自己的 Mac 后可以直接调用；若采集器仍接在你的 Windows 电脑上，这个包不能跨网络读它，需要另行设计服务端和客户端。

## 同门接收后从这里开始

前提：已安装 uv（可执行 `uv --version`）；选择 GitHub 方式还需要 Git。第一次同步会下载 Python/依赖，需要联网。无硬件也能先完成安装和演示测试。

### 方法一：接收 ZIP 并解压

解压收到的 `x518_force_api_20261006_提交号.zip`，得到完整的 `x518_force_api` 文件夹。将它放在机器人项目旁边，例如：

```text
工作目录/
├── Snake_Robot_XH430/    # 已有机器人项目，名称以实际为准
└── x518_force_api/       # 解压得到的传感器接口项目
```

在 Mac 终端进入解压目录（把路径换成自己的实际路径；不要只复制其中的 .py 文件）：

```bash
cd "/实际工作目录/x518_force_api"
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m x518_force --demo --count 3
```

预期：测试显示 `Ran 15 tests` 和 `OK`；演示首条 `raw=[101,-51]`，后续变化，且 `source="demo"`。ZIP 内没有 `.git`，更新时重新接收 ZIP；保留你自己写的配置和数据，不用 `git pull` 更新解压目录。

### 方法二：从 GitHub 获取与更新

首次获取用 **clone**；已经 clone 过之后更新用 **pull**。在准备存放项目的工作目录执行（若已有同名解压文件夹，请使用另一位置，避免混在一起）：

```bash
git clone https://github.com/AAA0error/x518-force-api.git x518_force_api
cd x518_force_api
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m x518_force --demo --count 3
```

以后在这个 clone 得到的目录更新：

```bash
git pull --ff-only
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

如果 pull 因本地修改或分支分歧拒绝执行，先检查 `git status` 并保留自己的修改，不要强制覆盖。要记录一次实验对应的软件版本，执行 `git rev-parse HEAD`，把完整提交号和实验记录一起保存。ZIP 文件名中的提交号同样标识源码版本。

### 两种方式拿到源码后：加入机器人项目

上面的演示运行在传感器项目自己的环境里。机器人程序要能 `import`，还需要把包加入**机器人项目的 uv 环境**。在机器人项目目录执行：

```bash
cd "/实际工作目录/Snake_Robot_XH430"
uv add --editable ../x518_force_api
uv run python -c "from x518_force import Config, X518Sensor; print('import OK')"
```

预期输出 `import OK`。这会修改机器人项目自己的 `pyproject.toml` 与 `uv.lock`；不要用传感器包的锁文件覆盖机器人项目的锁文件。机器人项目的 Python 必须满足 `>=3.10,<3.15`。本包默认独立环境用 Python 3.12；不会因此强制机器人项目改为 3.12。

使用可编辑安装后，接口源代码更新会直接反映到机器人环境；若接口依赖或项目元数据变更，在机器人项目里再执行 `uv sync`。保持两个项目的相对路径关系。

### 最后：接上传感器验证

将 USB-RS485 接到运行代码的电脑，关闭其他占用该串口的程序。在接口项目目录列出端口：

```bash
uv run --locked python -m x518_force --list-ports
```

Mac 用实际的 `/dev/cu.*` 端口；Windows 用实际的 `COM*` 端口。下面 Mac 的端口是占位符，必须替换：

```bash
uv run --locked python -m x518_force --port /dev/cu.usbserial-实际编号 --baud 115200 --slave 1 --decimals 2 --unit kg --interval 0.2 --count 100
```

真实数据应标记 `source="serial"`。依次空载、放上已知重物、移开重物、再放回，核对通道、方向和重复性；退出后再次读取，确认串口已释放。`--unit kg` 只是标签，必须核实设备实际单位和小数位。Mac 转换器驱动与真实载荷仍需实测，云端通过不能替代它。

GitHub Actions 已在 Windows、Mac Apple Silicon、Mac Intel，Python 3.10/3.12/3.14 共 **9 组任务全部通过**：[通过的运行记录](https://github.com/AAA0error/x518-force-api/actions/runs/37446329391)。该记录对应提交 `6412c4881f5a5d152aca14c507c93ef79913a287`；本次交付仅更新接入文档，程序代码相同。

## 环境与快速运行

暂定 Python 3.12，声明兼容范围 3.10–3.14；唯一运行依赖沿用 pyserial 3.5。开发机 uv 为 0.10.10，CI 固定此版本。与同门一样使用 Hatchling 构建，本包固定为 1.27.0（满足他的 `>=1.27.0`），另有可编辑安装所需的 editables 0.5；两者同时列入 dev 组，便于在项目环境内构建。`uv.lock` 锁定运行和开发依赖。

**已对齐的配置与待确认项**：2026-10-06，GitHub 插件读取失败，公开 GitHub API 返回 404；随后用户提供同门项目的 pyproject.toml：名称 `xh430-pure-python-control`，Python `>=3.10`，Hatchling `>=1.27.0`，依赖 dynamixel-sdk、PyYAML、pyserial `>=3.5`，可选 GUI 依赖 matplotlib/PyQt5。此包不需要舵机和 GUI 依赖，其 pyserial 3.5 满足同门约束，uv 合并项目依赖时仍需整体解析。已核对用户提供的机器人项目 lock，其中 pyserial 为 3.5；尚缺同门的 `.python-version` 和 `uv --version`，不能声称解释器与 uv 的精确版本已一致。若他使用 3.10–3.14，可将这里的 `.python-version` 改成相同版本，重新验证。若超出该范围，先验证再改支持范围。

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

Mac 使用实际 `/dev/cu.*` 端口；USB 转换器可能需要厂商的 macOS 驱动，取决于芯片型号。本项目当前只面向 Windows 和 macOS；pyserial 的平台支持不能替代你的转换器实测。[pyserial 平台说明](https://pyserial.readthedocs.io/en/latest/pyserial.html)

## 同门如何调用

将整个本目录交给同门，例如放在他的机器人仓库旁，命名为 `x518_force_api`。在**他的机器人项目目录**运行：

```text
uv add --editable ../x518_force_api
uv run python -c "from x518_force import Config, X518Sensor; print('import OK')"
```

这是同门修改自己项目依赖的操作，不在本次工作中执行。`uv add` 会更新他的 pyproject 和 lock；以后共享时相对路径应保持一致。稳定交付可运行 `uv build`，把 `dist/` 中的 `.whl` 交给他，再在他的项目里 `uv add /实际路径/x518_force-0.1.0-py3-none-any.whl`，避免源代码相对路径依赖。若以后使用 Git 依赖，应固定具体 commit；本仓库为 [AAA0error/x518-force-api](https://github.com/AAA0error/x518-force-api)。[uv 依赖管理](https://docs.astral.sh/uv/concepts/projects/dependencies/)

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

协议已根据《灵犀 x518双通道数据采集器操作手册v1-更新》PDF 第 7、12、13 页及原开发项目核对；交付包无需该 PDF 即可运行。仅发送 FC03，从 `0x0A00` 读 4 个 16-bit 寄存器；不清零、不标定、不写设备设置。协议实现沿用原开发项目。接收函数在性能调试后改用非阻塞串口和统一响应截止时间，避免每段接收重设 Windows 驱动超时；仍严格校验异常、短帧、CRC 和多余字节。

默认正确请求是 `01 03 0A 00 00 04 47 D1`。手册和任务书中的 `46 D1` 是 CRC 笔误；已用标准 CRC 和完整帧余数验证。示例响应 `01 03 08 00 00 00 06 FF FF 67 4B 77 F4` 解码为 `(6, -39093)`。支持高字在前和 `word_swap=True`。

默认 `raw/100`、kg 只是沿用已有项目配置假设；手册出厂单位是 N，实际设备未必相同。改 `unit="N"` **只改标签**，不换算读数。使用反馈前须与原厂显示、空载和已知载荷对照，确认两通道映射、方向、单位、小数位及标定。负数不是通信失败的充分证据。一次读取两路减少通信时差，但不证明设备同时采样。

## 没有 Mac，如何验证

本目录 `.github/workflows/compatibility.yml` 已配置 Windows、macOS Apple Silicon（`macos-15`）、macOS Intel（`macos-15-intel`），分别运行 Python 3.10/3.12/3.14。它验证 uv 安装、测试、演示、构建，以及在源码目录外安装 wheel 后调用；共 9 组任务。[GitHub 官方 runner 说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

1. 仓库地址：[AAA0error/x518-force-api](https://github.com/AAA0error/x518-force-api)。Actions 运行结果以 GitHub 页面为准。
2. 源码更新提交并推送后会触发测试；应包含隐藏的 `.github` 和 `uv.lock`，不上传 `.venv` 或本地实验数据。
3. 在 Actions 查看 `Python platform compatibility`；可用 Run workflow 手动触发，保留日志、Python/uv版本、runner架构和 commit。
4. 只有 Mac 两种架构对应的任务通过，才可以说这些软件测试在 macOS 上通过；修正后的运行结果以 Actions 页面为准。

公开仓库标准 runner 通常免费；私有仓库受免费分钟额度/计费规则约束，运行前查看自己的额度。Windows 上的 Docker/WSL 是 Linux 环境，不能充当 macOS 验证。[GitHub runner 资源与费用说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

云端 runner 不能访问你桌上的 USB-RS485，所以最终需要同门做以下 Mac 验收：记录 Mac/CPU/Python/uv/转换器芯片与驱动版本；列出实际端口；关闭其他串口工具；用确认过的参数连续读取；对照已知载荷与原厂读数；测试拔线报错、退出后端口释放、重新连接；测量实际读数间隔和延迟。软件测试通过并不证明硬件驱动、标定或控制稳定性。

## 文件与本次验证

- `x518_force/sensor.py`、`__init__.py`：公开接口、配置、样本、串口生命周期、合成演示。
- `x518_force/protocol.py`、`transport.py`：从既有实现复制的严格协议校验与分段接收。
- `x518_force/__main__.py`、`examples/read_force.py`：跨平台命令行/演示入口。
- `pyproject.toml`、`.python-version`、`uv.lock`、`.gitignore`：包安装、版本与环境管理。
- `tests/test_sensor.py`：协议错误、边界值、字序、分段接收、资源关闭与API/CLI测试。
- `.github/workflows/compatibility.yml`：Windows 与两种 Mac 的跨平台验证。

本地已在 Windows / Python 3.12.4 / uv 0.10.10 下完成以下验证：

- 使用原有环境通过 11 个离线测试、CLI 合成演示和 compileall。
- 经用户授权，仅在本项目 `.venv` 安装运行/构建依赖；`uv sync --locked --no-build-isolation --python 3.12 --no-python-downloads` 成功。
- 在 uv 项目环境再次通过 11 个测试和 `examples/read_force.py --demo`。
- `uv build --no-build-isolation --no-sources` 成功构建 sdist 和 wheel。
- 将 wheel 安装到同一 `.venv`，在源码目录之外验证导入路径确实来自 site-packages，调用返回 `(101, -51)`，并再次通过全部 11 个测试；随后恢复开发用可编辑安装。
- `uv lock --check --offline --python 3.12 --no-python-downloads` 通过。

本地构建采用预装开发依赖的方式，避免在 `.venv` 之外建立临时构建环境；Hatchling 的可编辑安装需要 editables，已显式声明以修复初次缺少该构建依赖的失败。普通目标主机可使用上面的 `uv sync --locked` 自动构建；CI 会验证这一标准流程。

后续 Windows COM3 三次真实读取成功，raw 为 `(86, -65719)`；缩放、单位和标定仍需加载/卸载对照。首次 Actions 中 Windows 的三个 Python 版本及两种 Mac 的 Python 3.12 全部通过；其余任务在最后的 wheel 安装检查失败，原因是测试配置解析 Python 符号链接后绕过了虚拟环境，已修正。按当前需求移除 Ubuntu，仅测试 Windows 和两种 Mac；修正后的 9 组任务已全部通过，见前面的运行记录。项目未配置独立 lint/typecheck 工具。云端离线测试不能替代 Mac 的真实串口验收。

已有环境也可直接在本目录 `python -m unittest discover -s tests -v`、`python -m x518_force --demo --count 3`；这验证源码运行，不能代替包安装验证。


## 串口读取性能调试（2026-10-06）

使用 COM3 / CH340 / 115200 / 8N1，目标频率 1000 Hz，实际有效事务频率由实测决定。设备内部采样档位只读确认是 8（1600 Hz），不等于主机读取频率。

旧版本平均一笔事务约 30.5 ms、约 32.7 Hz；对驱动操作计时发现重复设置 pyserial timeout 是显著开销。修正后 10 秒有效读取 628 次，零错误，约 62.71 Hz，平均 15.94 ms。这些是有效 Modbus 事务，不能证明每次是独立的新采样。

缓冲区诊断中首次可读通常已包含完整 13 字节，等待可读约 13 ms，解析约 31–33 微秒。把轮询间隔由 0.5 ms 改为 0.1 ms 收益很小，因此保留 0.5 ms，避免忙等。设备包间隔寄存器 0x063a 的只读 raw 为 10，按手册是 10 ms；它是否导致这些延迟需要改变该参数的对照测试，不能仅凭读数断言，USB/驱动和固件的延迟尚未独立分离。

```bash
uv run --locked python examples/benchmark_read_rate.py --port COM3 --hz 1000 --duration 10
```

脚本结束后将逐次数据和统计保存在 `dist/benchmarks/`，不逐条打印或写盘；只发测量 FC03。保持设备只读，不自动修改采样、包间隔、标定或清零。

当前报文请求 8 字节、响应 13 字节；115200、8N1 的纯线路耗时至少 1.823 ms，另有 2 ms 帧间隔和其他延迟。因此微秒级解析耗时不代表微秒级新数据读取，当前协议参数无法满足低于 1 ms 的完整读取周期。性能改动本地测试通过，尚未提交，也尚未在 Mac 云端验证；前面链接是此前版本的测试记录。
