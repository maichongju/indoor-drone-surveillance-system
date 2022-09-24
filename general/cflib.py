
from enum import Enum


class CFParameter(Enum):
    # PID Rate
    PID_RATE_ROLL_KP = 'pid_rate.roll_kp'
    PID_RATE_ROLL_KI = 'pid_rate.roll_ki'
    PID_RATE_ROLL_KD = 'pid_rate.roll_kd'
    PID_RATE_PITCH_KP = 'pid_rate.pitch_kp'
    PID_RATE_PITCH_KI = 'pid_rate.pitch_ki'
    PID_RATE_PITCH_KD = 'pid_rate.pitch_kd'
    PID_RATE_YAW_KP = 'pid_rate.yaw_kp'
    PID_RATE_YAW_KI = 'pid_rate.yaw_ki'
    PID_RATE_YAW_KD = 'pid_rate.yaw_kd'
