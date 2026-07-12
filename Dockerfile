FROM ubuntu:22.04

# 设置非交互式安装，避免卡住
ENV DEBIAN_FRONTEND=noninteractive

# 安装基础工具和 Java 17
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    wget \
    unzip \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置 JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# 下载并安装 Android 命令行工具
RUN wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmdline-tools.zip \
    && mkdir -p /opt/android-sdk/cmdline-tools \
    && unzip /tmp/cmdline-tools.zip -d /opt/android-sdk/cmdline-tools \
    && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest \
    && rm /tmp/cmdline-tools.zip

# 设置 ANDROID_SDK_ROOT
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$PATH
ENV PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH

# 接受许可并安装必要的 SDK 组件
RUN yes | sdkmanager --licenses
RUN sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" "ndk;27.0.12077973"

# 设置工作目录
WORKDIR /app

# 将项目文件复制到容器里
COPY . .

# 给 gradlew 执行权限
RUN chmod +x gradlew

# 构建 release APK
CMD ./gradlew --no-daemon assembleRelease