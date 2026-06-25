# RBPodo 사용 가이드

Rainbow Robotics RB-Series 협동 로봇과 TCP/IP 통신을 위한 rbpodo 라이브러리 사용 가이드.

---

## TCP 통신 구조

```
내 컴퓨터 (Python / C++) ──── TCP Port 5000 ──── RB 로봇 컨트롤 박스
                          ──── TCP Port 5001 ────
```

| 포트 | 용도 |
|------|------|
| **5000** | Command Channel — 명령 전송 및 응답 수신 |
| **5001** | Data Channel — 관절 각도, TCP 위치 등 실시간 상태 스트리밍 |

- 명령은 **텍스트 문자열**로 전송되며 `\n`으로 끝남
- 소켓은 **Non-blocking + TCP_NODELAY** 설정으로 연결됨
- 명령 전송 후 컨트롤 박스는 **ACK 메시지**로 수신 확인을 보냄
- 이동 시작/완료 등의 이벤트는 연결된 모든 프로세스에 **브로드캐스트**됨

---

## Python 설치

```bash
# PyPI에서 설치 (권장)
pip install rbpodo

# 또는 소스에서 빌드
cd rbpodo
pip install .
```

> **주의:** `pip install .`로 빌드하려면 pybind11 등 추가 의존성이 필요함.  
> 일반적으로 PyPI 설치를 권장.

---

## 핵심 클래스

### `Cobot`

로봇과의 연결 및 모든 명령을 담당하는 메인 클래스.

```python
robot = rb.Cobot("10.0.2.7")        # 기본 포트 5000
robot = rb.Cobot("10.0.2.7", 5000)  # 포트 명시
```

생성자 호출 시 즉시 TCP 연결을 시도하며, 연결 실패 시 예외를 던짐.

---

### `ResponseCollector`

컨트롤 박스에서 오는 응답 메시지를 수집하는 큐.  
모든 명령 함수의 첫 번째 인자로 전달됨.

```python
rc = rb.ResponseCollector()
```

응답 타입:

| 타입 | 의미 |
|------|------|
| `ACK` | 명령 수신 확인 |
| `Info` | 정보성 메시지 (이동 완료 등) |
| `Warn` | 경고 |
| `Error` | 에러 |

유용한 메서드:

```python
rc.error()               # 에러 응답만 필터링
rc.error().throw_if_not_empty()  # 에러 있으면 예외 발생
rc.has_error()           # 에러 존재 여부 확인
rc.clear()               # 수집된 응답 초기화
```

---

### `ReturnType`

각 명령 함수의 반환값. 명령 성공/실패/타임아웃 여부를 나타냄.

```python
ret = robot.move_j(rc, ...)
ret.type()        # ReturnType.Success / Timeout / Error
ret.is_success()  # bool
ret.is_timeout()  # bool
ret.is_error()    # bool
```

---

## 기본 사용 패턴

```python
import rbpodo as rb
import numpy as np

ROBOT_IP = "10.0.2.7"

robot = rb.Cobot(ROBOT_IP)
rc = rb.ResponseCollector()

# 1. 운영 모드 설정 (실제 동작 전 반드시 설정)
robot.set_operation_mode(rc, rb.OperationMode.Simulation)  # 시뮬레이션
# robot.set_operation_mode(rc, rb.OperationMode.Real)       # 실제 로봇

# 2. 속도 설정 (0~1, UI의 속도 바)
robot.set_speed_bar(rc, 0.5)

# 3. 버퍼 초기화 (이전 응답 메시지 제거)
robot.flush(rc)

# 4. 이동 명령
robot.move_j(rc, np.array([100, 0, 0, 0, 0, 0]), 200, 400)

# 5. 이동 완료 대기
if robot.wait_for_move_started(rc, 0.1).type() == rb.ReturnType.Success:
    robot.wait_for_move_finished(rc)

# 6. 에러 확인
rc.error().throw_if_not_empty()
```

---

## 주요 API

### 설정

```python
robot.set_operation_mode(rc, rb.OperationMode.Simulation)   # 시뮬레이션 모드
robot.set_operation_mode(rc, rb.OperationMode.Real)          # 실제 로봇 모드
robot.set_speed_bar(rc, 0.5)                                 # 전체 속도 (0~1)
robot.set_speed_multiplier(rc, 1.0)                          # 속도 배율 (0~2)
robot.set_acc_multiplier(rc, 1.0)                            # 가속도 배율 (0~2)
robot.set_speed_acc_j(rc, speed, accel)                      # J계열 고정 속도/가속도 (deg/s, deg/s²)
robot.set_speed_acc_l(rc, speed, accel)                      # L계열 고정 속도/가속도 (mm/s, mm/s²)
robot.set_collision_onoff(rc, True)                          # 충돌 감지 on/off
robot.activate(rc)                                            # 로봇 활성화
```

### 상태 조회

```python
robot.get_robot_state(rc, robot_state)    # Idle / Moving
robot.get_tcp_info(rc, point)             # 현재 TCP 위치/자세 (mm & deg)
robot.get_tfc_info(rc, point)             # 현재 TFC 위치/자세
robot.get_control_box_info(rc, info)      # 컨트롤 박스 정보
robot.get_system_variable(rc, rb.SystemVariable.SD_J0_ANG, val)  # 시스템 변수 조회
```

### 이동 명령

#### MoveJ — 관절 공간 이동

```python
# joint: [J0, J1, J2, J3, J4, J5] (단위: deg)
# speed: deg/s, acceleration: deg/s²
robot.move_j(rc, np.array([0, 0, 90, 0, 90, 0]), speed=60, acceleration=80)
```

#### MoveL — 직선 이동 (TCP 기준)

```python
# point: [X, Y, Z, Rx, Ry, Rz] (단위: mm & deg)
# speed: mm/s, acceleration: mm/s²
robot.move_l(rc, np.array([400, 0, 300, 0, 180, 0]), speed=100, acceleration=200)
```

#### MoveL_rel — 상대 직선 이동

```python
# frame: rb.ReferenceFrame.Base / Tool / User0 / User1 / User2
robot.move_l_rel(rc, np.array([0, 100, -200, 0, 0, 0]), 300, 400, rb.ReferenceFrame.Base)
```

#### MoveJL — TCP 목표를 MoveJ 방식으로 이동

```python
robot.move_jl(rc, np.array([400, 0, 300, 0, 180, 0]), speed=20, acceleration=5)
```

#### MovePB — 경유점 직선 블렌딩

```python
robot.move_pb_clear(rc)
robot.move_pb_add(rc, np.array([400, 100, 300, 0, 180, 0]), speed=100,
                  option=rb.BlendingOption.Ratio, blending_value=0.5)
robot.move_pb_add(rc, np.array([400, -100, 300, 0, 180, 0]), speed=100,
                  option=rb.BlendingOption.Ratio, blending_value=0.5)
robot.move_pb_run(rc, acceleration=200, option=rb.MovePBOption.Intended)
```

#### MoveJB2 — 관절 공간 블렌딩

```python
robot.move_jb2_clear(rc)
robot.move_jb2_add(rc, np.array([90, 0, 0, 0, 0, 0]), speed=100, acceleration=100, blending_value=5.0)
robot.move_jb2_add(rc, np.array([0, 0, 0, 0, 0, 0]), speed=100, acceleration=100, blending_value=5.0)
robot.move_jb2_run(rc)
```

#### MoveC — 원호 이동

```python
# via_point를 거쳐 target_point까지 원호로 이동
robot.move_c_points(rc, via_point, target_point, speed=50, acceleration=100,
                    option=rb.MoveCOrientationOption.Intended)
```

### 이동 대기

```python
robot.wait_for_move_started(rc, timeout=0.1)  # 이동 시작 대기 (timeout: 초)
robot.wait_for_move_finished(rc)               # 이동 완료 대기

# 또는 상태 폴링으로 대기
while robot.get_robot_state(rc)[1] == rb.RobotState.Moving:
    time.sleep(0.001)
```

### flush

```python
robot.flush(rc)  # 버퍼에 남은 이전 응답 메시지 제거
```

**이동 명령 전 반드시 호출.** 이전 이동의 완료 메시지가 버퍼에 남아 있으면 `wait_for_move_finished`가 잘못 반환할 수 있음.

### I/O 제어

```python
robot.set_box_dout(rc, port=0, mode=rb.DigitalIOMode.High)   # 디지털 출력 on
robot.set_box_dout(rc, port=0, mode=rb.DigitalIOMode.Low)    # 디지털 출력 off
robot.set_box_aout(rc, port=0, voltage=5.0)                  # 아날로그 출력 (0~10V)
```

---

## 데이터 채널 (Port 5001)

실시간 로봇 상태를 고속으로 수신하려면 별도로 Port 5001에 연결.

```python
import rbpodo as rb

data_channel = rb.CobotData("10.0.2.7")
state = data_channel.request_data()

print(state.sdata.jnt_ref)   # 관절 참조 각도 [6] (deg)
print(state.sdata.jnt_ang)   # 관절 실제 각도 [6] (deg)
print(state.sdata.tcp_ref)   # TCP 위치/자세 [6] (mm & deg)
print(state.sdata.jnt_cur)   # 관절 전류 [6] (A)
print(state.sdata.robot_state)  # 1=Idle, 3=Moving
```

`SystemState` 구조체 주요 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `jnt_ref[6]` | float | 관절 참조(목표) 각도 (deg) |
| `jnt_ang[6]` | float | 관절 실제 측정 각도 (deg) |
| `jnt_cur[6]` | float | 관절 전류 (A) |
| `tcp_ref[6]` | float | 참조 관절 기준 TCP 위치/자세 (mm & deg) |
| `tcp_pos[6]` | float | 실제 관절 기준 TCP 위치/자세 (mm & deg) |
| `robot_state` | int | 1=Idle, 3=Moving |
| `digital_in[16]` | int | 디지털 입력 (0 or 1) |
| `digital_out[16]` | int | 디지털 출력 (0 or 1) |
| `analog_in[4]` | float | 아날로그 입력 전압 (V) |
| `jnt_temperature[6]` | float | 관절 온도 (°C) |

---

## wait 함수 주의사항

`wait_for_move_finished` 등의 wait 함수는 컨트롤 박스가 보내는 이벤트 메시지를 파싱해 동작함. 주의해야 할 두 가지 상황:

**1. 다중 프로세스 연결 시 오작동 가능**  
다른 프로세스에서 발생한 에러 메시지가 모든 연결에 브로드캐스트되어, 관계없는 에러로 인해 wait 함수가 조기 반환할 수 있음.  
→ 해결: 상태 폴링 방식으로 대기

```python
while robot.get_robot_state(rc)[1] == rb.RobotState.Moving:
    time.sleep(0.001)
```

**2. flush 없이 wait 사용 시 오작동 가능**  
버퍼에 이전 이동의 완료 메시지가 남아 있으면, 현재 이동이 시작되기도 전에 완료로 잘못 판단함.  
→ 해결: 이동 명령 전 `robot.flush(rc)` 호출

---

## 전체 예제

```python
import rbpodo as rb
import numpy as np
import time

ROBOT_IP = "10.0.2.7"

def main():
    try:
        robot = rb.Cobot(ROBOT_IP)
        rc = rb.ResponseCollector()

        # 시뮬레이션 모드, 속도 50%
        robot.set_operation_mode(rc, rb.OperationMode.Simulation)
        robot.set_speed_bar(rc, 0.5)
        robot.flush(rc)

        # MoveJ: 관절 각도 [100, 0, 0, 0, 0, 0]도로 이동
        robot.move_j(rc, np.array([100, 0, 0, 0, 0, 0]), 200, 400)
        if robot.wait_for_move_started(rc, 0.1).type() == rb.ReturnType.Success:
            robot.wait_for_move_finished(rc)

        robot.flush(rc)

        # MoveL: TCP를 직선으로 이동
        robot.move_l(rc, np.array([400, 0, 500, 0, 180, 0]), 100, 200)
        if robot.wait_for_move_started(rc, 0.1).type() == rb.ReturnType.Success:
            robot.wait_for_move_finished(rc)

        rc.error().throw_if_not_empty()
        print("완료")

    except Exception as e:
        print(f"에러: {e}")

if __name__ == "__main__":
    main()
```

---

## 네트워크 구성

### 권장 구성: 와이파이 동글 + 랜선 1개

```
인터넷 ──── Wi-Fi 동글 ──── PC
로봇 컨트롤 박스 ──── 랜선(LAN) ──── PC (enp14s0)
```

- 인터넷은 Wi-Fi 동글, 로봇 통신은 기존 랜 포트 전용으로 분리
- 라우팅 충돌 없이 깔끔하게 분리됨
- 로봇 제어에서 중요한 건 인터넷 속도가 아니라 로봇-PC 간 연결 안정성

### 랜 포트 고정 IP 설정 (필수)

로봇 컨트롤 박스는 DHCP 서버가 없어서 자동 IP 배정이 안 됨.  
랜 포트에 수동으로 고정 IP를 설정해야 함.

| 항목 | 값 |
|---|---|
| IP 주소 | `10.0.2.100` (10.0.2.x 중 7 제외 아무거나) |
| 서브넷 마스크 | `255.255.255.0` |
| 게이트웨이 | 비워도 됨 (인터넷은 Wi-Fi로) |

**Ubuntu에서 설정하는 방법:**

```bash
# 현재 인터페이스 이름 확인
ip link show

# 고정 IP 설정 (enp14s0에 적용)
sudo nmcli con mod netplan-enp14s0 \
  ipv4.method manual \
  ipv4.addresses 10.0.2.100/24 \
  ipv4.gateway "" \
  ipv4.dns ""

sudo nmcli con up netplan-enp14s0

# 설정 확인
ip addr show enp14s0
```

**설정 후 연결 확인:**

```bash
ping 10.0.2.7   # 로봇 컨트롤 박스 응답 확인
```

**원래대로 되돌리기 (DHCP로 복구):**

```bash
sudo nmcli con mod netplan-enp14s0 \
  ipv4.method auto \
  ipv4.addresses "" \
  ipv4.gateway "" \
  ipv4.dns ""

sudo nmcli con up netplan-enp14s0
```

> **주의:** Wi-Fi 동글 연결 전에 랜 포트를 고정 IP로 바꾸면 인터넷이 끊김.  
> 반드시 Wi-Fi 동글로 인터넷 연결을 먼저 확인한 뒤 랜 포트 설정을 변경할 것.

---

## 실제 로봇 연결 체크리스트

1. Wi-Fi 동글로 인터넷 연결 확인
2. 랜 포트 고정 IP `10.0.2.100` 설정
3. 랜선으로 PC와 로봇 컨트롤 박스 연결
4. `ping 10.0.2.7` 으로 통신 가능 여부 확인
5. 방화벽에서 포트 5000, 5001 허용
6. 처음에는 반드시 `OperationMode.Simulation`으로 테스트
7. 실제 동작 시 `OperationMode.Real` 로 변경
8. 비상정지 버튼(E-Stop) 접근 가능한 상태에서 동작
