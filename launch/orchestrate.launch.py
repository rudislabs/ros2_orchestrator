from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, LogInfo, DeclareLaunchArgument, SetLaunchConfiguration, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.descriptions import ParameterValue
from launch_ros.actions import Node

import os
from time import sleep
import json
import shlex
import sys
import subprocess

# Set relative paths to real paths
launchPath = os.path.realpath(__file__).replace("orchestrate.launch.py","")
jsonPath = os.path.realpath(os.path.relpath(os.path.join(launchPath,"../config")))
workSpaceROS2 = os.path.realpath(os.path.relpath(os.path.join(launchPath,"../../..")))


# Initialize flags
hasBuiltROS2Pkgs=False
debugVerbose=False


# Open JSON configuration file
with open('{:s}/config.json'.format(jsonPath)) as jsonFile:
    jsonParams = json.load(jsonFile)

#Assume nothing is in json
setupSystem=setupROS2=ROS2Nodes = None

# Setup related configs
if "setup" in jsonParams:
    setup = jsonParams["setup"]
    if "system" in setup:
        setupSystem = setup["system"]
    if "ros2" in setup:
        setupROS2 = setup["ros2"]


# Runtime related params
if "nodes" in jsonParams:
    ROS2Nodes= jsonParams["nodes"]

########################################################################################
if setupSystem is not None:
    # Set environment variables if present
    if "setEnvironment" in setupSystem:
        for env in setupSystem["setEnvironment"]:
            setEnv = setupSystem["setEnvironment"][env]
            if setEnv["method"] == "overwrite":
                os.environ[setEnv["variable"]] = setEnv["value"]
            elif setEnv["method"] == "prepend":
                if os.getenv(setEnv["variable"]) is None:
                    os.environ[setEnv["variable"]] = setEnv["value"]
                else:
                    os.environ[setEnv["variable"]] = '{:s}:{:s}'.format(
                        setEnv["value"], os.getenv(setEnv["variable"]))
            elif setEnv["method"] == "postpend":
                if os.getenv(setEnv["variable"]) is None:
                    os.environ[setEnv["variable"]] = setEnv["value"]
                else:
                    os.environ[setEnv["variable"]] = '{:s}:{:s}'.format(
                        os.getenv(setEnv["variable"]), setEnv["value"])

########################################################################################

if setupROS2 is not None:
    for build in setupROS2:
        buildROS2Pkg = setupROS2[build]
        pathROS2Pkg = '{:s}/src/{:s}'.format(workSpaceROS2,buildROS2Pkg["build"]["package"])
        if (not os.path.isdir(pathROS2Pkg)):
            hasBuiltROS2Pkgs=True
            cmdClone = 'git clone -b {:s} {:s} {:s}'.format(
                buildROS2Pkg["version"],buildROS2Pkg["repo"], pathROS2Pkg)
            cmdClonePopen=shlex.split(cmdClone)
            clonePopen = subprocess.Popen(cmdClonePopen, 
                stdout=subprocess.PIPE, text=True)
            while True:
                output = clonePopen.stdout.readline()
                if output == '' and clonePopen.poll() is not None:
                    break
                if output:
                    print(output.strip())
            clonePopen.wait()

            build_cmd = 'colcon build {:s} {:s} {:s}'.format(
                buildROS2Pkg["build"]["prefix"],buildROS2Pkg["build"]["package"],
                buildROS2Pkg["build"]["postfix"])
            build_cmdPopen=shlex.split(build_cmd)
            buildPopen = subprocess.Popen(build_cmdPopen, stdout=subprocess.PIPE, 
                cwd=workSpaceROS2, text=True)
            while True:
                output = buildPopen.stdout.readline()
                if output == '' and buildPopen.poll() is not None:
                    break
                if output:
                    print(output.strip())
            buildPopen.wait()

    # Require restart if colcon packages built so they can be correctly found
    if hasBuiltROS2Pkgs:
        os.system('/bin/bash {:s}/install/setup.bash'.format(workSpaceROS2))
        os.system("/bin/bash /opt/ros/galactic/setup.bash")
        print('''\n\n\nPLEASE RUN:\n 
            source {:s}/install/setup.bash; ros2 launch ros2_orchestrator orchestrate.launch.py
            \n\n'''.format(workSpaceROS2))
        sys.exit()

########################################################################################

def generate_launch_description():
    launchConfigWorld=LaunchConfiguration('world')
    ld = LaunchDescription([])

    if ROS2Nodes is not None:
        for ROS2Node in ROS2Nodes:
            node = ROS2Nodes[ROS2Node]
            if "remappings" in node:
                remappings = [eval(str(node["remappings"]))]
                if "arguments" in node:
                    runNode = Node(package=node["package"],
                        executable=node["executable"],
                        name=str(node["name"]), 
                        output=node["output"],
                        arguments=node["arguments"],
                        parameters=node["parameters"],
                        remappings=remappings)
                else:
                    runNode = Node(package=node["package"],
                        executable=node["executable"],
                        name=str(node["name"]), 
                        output=node["output"],
                        parameters=node["parameters"],
                        remappings=remappings)
            else:
                if "arguments" in node:
                    runNode = Node(package=node["package"],
                        executable=node["executable"],
                        name=str(node["name"]), 
                        output=node["output"],
                        arguments=node["arguments"],
                        parameters=node["parameters"])
                else:
                    runNode = Node(package=node["package"],
                        executable=node["executable"],
                        name=str(node["name"]), 
                        output=node["output"],
                        parameters=node["parameters"])

            ld.add_action(runNode)

    ####################################################################################


    return ld
