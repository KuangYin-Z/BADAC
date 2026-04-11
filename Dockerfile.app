FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        bison \
        curl \
        flex \
        git \
        libfl-dev \
        libgmp-dev \
        libssl-dev \
        m4 \
        pkg-config \
        python3 \
        python3-dev \
        python3-pip \
        wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

RUN wget -q https://crypto.stanford.edu/pbc/files/pbc-1.0.0.tar.gz \
    && tar -xzf pbc-1.0.0.tar.gz \
    && cd pbc-1.0.0 \
    && ./configure \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig

WORKDIR /work

COPY app/req.txt /work/app/req.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir -r /work/app/req.txt

COPY bridge/package.json /work/bridge/package.json
RUN cd /work/bridge && npm install --omit=dev

COPY app /work/app
COPY bridge /work/bridge

EXPOSE 8000

CMD ["python3", "-m", "app.server"]
