ARG ROS_DISTRO=jazzy
FROM osrf/ros:${ROS_DISTRO}-ros-base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG USERNAME=ros
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=${ROS_DISTRO}
ENV AMR_WS=/workspaces/ros2_ws
ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    curl \
    git \
    make \
    sudo \
    python3-colcon-common-extensions \
    python3-pip \
    python3-venv \
    ros-${ROS_DISTRO}-action-msgs \
    ros-${ROS_DISTRO}-ament-index-python \
    ros-${ROS_DISTRO}-geometry-msgs \
    ros-${ROS_DISTRO}-launch \
    ros-${ROS_DISTRO}-launch-ros \
    ros-${ROS_DISTRO}-lifecycle-msgs \
    ros-${ROS_DISTRO}-nav2-msgs \
    ros-${ROS_DISTRO}-rclpy \
    ros-${ROS_DISTRO}-tf2-ros \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/amr_requirements.txt

RUN python3 -m pip install --no-cache-dir -r /tmp/amr_requirements.txt \
    && rm -f /tmp/amr_requirements.txt

RUN if ! getent group ${USER_GID} >/dev/null; then groupadd --gid ${USER_GID} ${USERNAME}; fi \
    && if ! id -u ${USERNAME} >/dev/null 2>&1; then useradd --gid ${USER_GID} -m -s /bin/bash ${USERNAME}; fi \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && mkdir -p ${AMR_WS}/src \
    && chown -R ${USERNAME}:${USER_GID} ${AMR_WS}

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /etc/bash.bashrc \
    && echo 'if [ -f /workspaces/ros2_ws/install/setup.bash ]; then source /workspaces/ros2_ws/install/setup.bash; fi' >> /etc/bash.bashrc

WORKDIR ${AMR_WS}
USER ${USERNAME}
