import rbpodo as rb
import numpy as np

ROBOT_IP = "10.0.2.7"


def _main():
    try:
        robot = rb.Cobot(ROBOT_IP)
        rc = rb.ResponseCollector()

        robot.set_operation_mode(rc, rb.OperationMode.Real)
        robot.set_speed_bar(rc, 0.1)
        robot.flush(rc)

        # 이동 전 TCP 위치 확인
        _, before = robot.get_tcp_info(rc)
        print(f"이동 전 TCP: {before}")

        print("MoveJ 시작: [0, 0, 0, 0, 0, 0]")
        robot.move_j(rc, np.array([0, 0, 0, 0, 0, 0]), 200, 400)
        if robot.wait_for_move_started(rc, 0.1).type() == rb.ReturnType.Success:
            print("이동 시작됨")
            robot.wait_for_move_finished(rc)
            print("이동 완료")

        # 이동 후 TCP 위치 확인
        _, after = robot.get_tcp_info(rc)
        print(f"이동 후 TCP: {after}")

        rc.error().throw_if_not_empty()
        print("에러 없음 - 성공")

    except Exception as e:
        print(f"에러: {e}")


if __name__ == "__main__":
    _main()
