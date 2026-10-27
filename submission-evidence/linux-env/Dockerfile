FROM ubuntu@sha256:86eb1bc1059720a19a777ba5a109e9ee3690d5dfe3e319871a6d6beb86fb7f85
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build pkg-config git ca-certificates \
    python3 python3-dev python3-venv libsqlite3-dev libssl-dev nlohmann-json3-dev \
    libzstd-dev libtiff-dev libcurl4-openssl-dev libblosc-dev \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/testenv && /opt/testenv/bin/pip install 'nanobind>=2.10.2' numpy pytest
COPY opencv-4.14.0.tar.gz /tmp/opencv.tar.gz
RUN echo 'ee8fb9b30eb60850431b4656447080e3737b56e45719c92b67f245950609f86e  /tmp/opencv.tar.gz' | sha256sum -c - \
    && mkdir /tmp/opencv-src && tar -xf /tmp/opencv.tar.gz -C /tmp/opencv-src --strip-components=1 \
    && cmake -S /tmp/opencv-src -B /tmp/opencv-build -G Ninja \
       -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/opencv \
       -DBUILD_LIST=core -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF \
       -DBUILD_EXAMPLES=OFF -DBUILD_opencv_apps=OFF -DBUILD_JAVA=OFF \
       -DBUILD_opencv_python2=OFF -DBUILD_opencv_python3=OFF \
       -DWITH_OPENCL=OFF -DWITH_IPP=OFF -DWITH_ITT=OFF -DWITH_LAPACK=OFF -DWITH_PROTOBUF=OFF \
    && cmake --build /tmp/opencv-build -j 2 && cmake --install /tmp/opencv-build \
    && rm -rf /tmp/opencv-build /tmp/opencv-src /tmp/opencv.tar.gz
ENV PATH="/opt/testenv/bin:${PATH}"
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openssh-client openssh-sftp-server && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 501 --gid 20 --no-create-home --shell /bin/sh reviewer
WORKDIR /work
