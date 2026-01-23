# Docker/QEMU Emulation - WebStatusπ

Optional ARM emulation for full Raspberry Pi environment simulation.

**Note**: For most development tasks, using mocks (see [MOCKING.md](MOCKING.md)) is simpler and faster. Docker/QEMU is useful for:
- Testing ARM-specific behavior
- Verifying compatibility with Pi libraries
- CI/CD pipelines requiring ARM builds

## Dockerfile for ARM Emulation

```dockerfile
# Dockerfile
FROM arm32v7/python:3.7-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Run in mock mode if no hardware
ENV MOCK_GPIO=true
ENV MOCK_DISPLAY=true

CMD ["python3", "main.py"]
```

## Build and Run Script

```bash
#!/bin/bash
# build_and_test.sh

# Build Docker image
docker build -t webstatuspi-test .

# Run in container
docker run --rm -it \
    -v $(pwd)/data:/app/data \
    -p 8080:8080 \
    webstatuspi-test
```

## QEMU Setup (for non-ARM hosts)

To run ARM containers on x86/x64 machines:

```bash
# Install QEMU user-mode emulation
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify ARM emulation works
docker run --rm arm32v7/python:3.7-slim python3 --version
```

## Docker Compose (Optional)

```yaml
# docker-compose.yml
version: '3.8'
services:
  webstatuspi:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - MOCK_GPIO=true
      - MOCK_DISPLAY=true
      - DEBUG=true
```

Run with:

```bash
docker-compose up --build
```

## When to Use Docker vs Mocks

| Scenario | Recommended |
|----------|-------------|
| Quick development iteration | Mocks |
| Unit testing | Mocks |
| Testing ARM-specific code | Docker/QEMU |
| CI/CD pipeline | Docker/QEMU |
| Testing on real Pi | Deploy directly |

## Performance Considerations

- QEMU emulation is **slow** (~10x slower than native)
- Use mocks for rapid development cycles
- Reserve Docker/QEMU for integration testing
- For best results, test on actual Raspberry Pi hardware

## Additional Resources

- [Docker multi-arch builds](https://docs.docker.com/build/building/multi-platform/)
- [QEMU user-mode documentation](https://www.qemu.org/docs/master/user/main.html)
- [multiarch/qemu-user-static](https://github.com/multiarch/qemu-user-static)
