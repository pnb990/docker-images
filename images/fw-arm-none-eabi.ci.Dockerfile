# Base of all images
FROM nodejs:25-trixie

# -------------------------------------------------------------------
# Configuration and Environment Variables
# -------------------------------------------------------------------
ARG ARM_TOOLCHAIN_VERSION=13.2.rel1
ARG ARM_DL_LINK=https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu/${ARM_TOOLCHAIN_VERSION}/binrel/arm-gnu-toolchain-${ARM_TOOLCHAIN_VERSION}-x86_64-arm-none-eabi.tar.xz

ENV ARM_TOOLCHAIN_DIR=/opt/gnu_arm/${ARM_TOOLCHAIN_VERSION}
ENV PATH=${ARM_TOOLCHAIN_DIR}/bin:$PATH
ENV AM_I_IN_A_DOCKER_CONTAINER=1

# -------------------------------------------------------------------
# Base Tool Install
# -------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    build-essential \
    git \
    wget \
    bzip2 \
    ca-certificates \
    python3 \
    pipenv \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# -------------------------------------------------------------------
# Install ARM Toolchain
# -------------------------------------------------------------------
RUN mkdir -p ${ARM_TOOLCHAIN_DIR} /tmp/arm-toolchain \
    && wget -qO- ${ARM_DL_LINK} | tar -xJ -C /tmp/arm-toolchain --strip-components=1 \
    && mv /tmp/arm-toolchain/* ${ARM_TOOLCHAIN_DIR} \
    && rm -rf /tmp/arm-toolchain
ENV TOOLCHAIN_DEVCONTAINER_DIR=${ARM_TOOLCHAIN_DIR}


