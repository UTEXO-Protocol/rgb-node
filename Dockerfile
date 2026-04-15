# rgb_lib wheel is cp311 + manylinux x86_64; use 3.11 and amd64 for compatibility
FROM --platform=linux/amd64 python:3.11-slim-bookworm

# libuniffi.so needs OpenSSL and libgcc at runtime; slim image omits them by default.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libgcc-s1 \
    libstdc++6 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY source/rgb_lib-0.3.0b17-cp311-cp311-manylinux_2_35_x86_64.whl ./source/
COPY . .

RUN sed '/^rgb-lib/d' requirements.txt > /tmp/requirements-docker.txt && \
    pip install --no-cache-dir -r /tmp/requirements-docker.txt && \
    pip install --no-cache-dir ./source/rgb_lib-0.3.0b17-cp311-cp311-manylinux_2_35_x86_64.whl && \
    cd "$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')/rgb_lib" && \
    ln -sf librgblibuniffi.so libuniffi.so

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

