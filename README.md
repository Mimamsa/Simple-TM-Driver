# Simple TM Driver

This repository is a minified version of TM ROS2 driver (https://github.com/TechmanRobotInc/tmr_ros2/tree/humble), provides an option to control TechMan robotic arm without without ROS or ROS2.

This driver applies to TechMan TM5-900 robotic arm by default.


## Feature

- Only PTPJ and PTPC function calls implemented as of now.


## Installation

```
pip install -r requirements.txt
```

## Usaage

### Configure networking
Please follow the instructions of [README.md from TM ROS2 driver](https://github.com/TechmanRobotInc/tmr_ros2/tree/humble) to setup TM5-900 and make sure the following parts are finished:

1. Listen task of flow project
2. Network
3. Remote connection to TM ROBOT
4. Data Table Setting

Remark: The TM robot and the laptop execute send script should be in the same local network.

### Send script to TM robot

```
python3 main.py -ip [IP address of robotic arm]
```