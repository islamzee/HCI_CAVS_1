cmake_minimum_required(VERSION 3.8)
project(mtx_nav2_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ArbiterStatus.msg"
  "msg/CanFrame.msg"
  "msg/DriveCommand.msg"
  "msg/SafetyStatus.msg"
  DEPENDENCIES std_msgs)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
