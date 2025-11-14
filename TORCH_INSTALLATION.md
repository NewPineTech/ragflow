# PyTorch Installation in Docker

**File:** `Dockerfile`  
**Lines:** 165-180  
**Date:** November 14, 2025

---

## 🔧 What Was Added

PyTorch installation after Python dependencies:

```dockerfile
# Install PyTorch (CPU version for lighter image)
RUN --mount=type=cache,id=ragflow_pip,target=/root/.cache/pip,sharing=locked \
    source ${VIRTUAL_ENV}/bin/activate && \
    if [ "$NEED_MIRROR" == "1" ]; then \
        pip install torch torchvision torchaudio --index-url https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cpu; \
    else \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi
```

---

## 📦 Packages Installed

- **torch** - Core PyTorch library
- **torchvision** - Image/video datasets and models
- **torchaudio** - Audio processing utilities

---

## 🎯 Version Options

### Option 1: CPU-only (Current - Default)
```dockerfile
# Lightweight, works everywhere
--index-url https://download.pytorch.org/whl/cpu
```

**Pros:**
- ✅ Smaller image size (~500MB vs 2GB+)
- ✅ Works on any hardware
- ✅ Faster build time
- ✅ Good for inference

**Use for:**
- Production deployments without GPU
- Development/testing
- Inference workloads

### Option 2: CUDA 11.8 (GPU Support)
```dockerfile
# Uncomment these lines in Dockerfile (lines 170-177)
# For CUDA 11.8 (uncomment if GPU support needed):
RUN --mount=type=cache,id=ragflow_pip,target=/root/.cache/pip,sharing=locked \
    source ${VIRTUAL_ENV}/bin/activate && \
    if [ "$NEED_MIRROR" == "1" ]; then \
        pip install torch torchvision torchaudio --index-url https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cu118; \
    else \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; \
    fi
```

**Pros:**
- ✅ GPU acceleration (much faster)
- ✅ Required for training
- ✅ Better for heavy inference

**Requires:**
- NVIDIA GPU
- CUDA 11.8 drivers
- nvidia-docker runtime

---

## 🌍 China Mirror Support

Automatically uses TUNA mirrors when `NEED_MIRROR=1`:

```bash
# Build with China mirrors
docker build --build-arg NEED_MIRROR=1 -t ragflow .
```

**Mirror URLs:**
- CPU: `https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cpu`
- CUDA: `https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/cu118`

---

## 🏗️ Build Commands

### Standard build (CPU):
```bash
docker build -t ragflow:latest .
```

### Build with China mirrors:
```bash
docker build --build-arg NEED_MIRROR=1 -t ragflow:latest .
```

### Build with GPU support:
```bash
# 1. Edit Dockerfile: Comment out CPU lines (166-170), uncomment CUDA lines (171-177)
# 2. Build:
docker build -t ragflow:gpu .
```

---

## 🧪 Verify Installation

After building, check PyTorch:

```bash
# Start container
docker run -it ragflow:latest bash

# Test PyTorch
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**Expected output (CPU):**
```
PyTorch: 2.5.1+cpu
CUDA available: False
```

**Expected output (GPU):**
```
PyTorch: 2.5.1+cu118
CUDA available: True
```

---

## 📊 Image Size Impact

| Version | Size | Build Time |
|---------|------|------------|
| Without PyTorch | ~2.5GB | 10 min |
| With PyTorch CPU | ~3.0GB | 12 min |
| With PyTorch CUDA | ~4.5GB | 15 min |

---

## ⚠️ Troubleshooting

### Issue: Slow download
**Solution:** Use mirrors
```bash
docker build --build-arg NEED_MIRROR=1 -t ragflow .
```

### Issue: Out of space
**Solution:** Clean Docker cache
```bash
docker system prune -a
docker builder prune -a
```

### Issue: CUDA version mismatch
**Solution:** Check your GPU driver
```bash
nvidia-smi  # Check CUDA version
# Use matching PyTorch version (cu118, cu121, etc.)
```

### Issue: Import error
**Solution:** Verify virtual env
```bash
# Inside container
which python3  # Should be /ragflow/.venv/bin/python3
pip list | grep torch
```

---

## 🔄 Switching Between CPU and GPU

### To switch to GPU:
1. Edit `Dockerfile` lines 166-177
2. Comment CPU lines (166-170)
3. Uncomment CUDA lines (171-177)
4. Rebuild: `docker build -t ragflow:gpu .`

### To switch back to CPU:
1. Uncomment CPU lines
2. Comment CUDA lines
3. Rebuild: `docker build -t ragflow:latest .`

---

## 📚 PyTorch Usage in RAGFlow

PyTorch can be used for:
- **Embedding models** - Local model inference
- **Reranking** - Cross-encoder models
- **Image processing** - Vision models (torchvision)
- **Audio processing** - Speech models (torchaudio)
- **Custom models** - Fine-tuned transformers

Example:
```python
import torch
from transformers import AutoModel, AutoTokenizer

# Load model
model = AutoModel.from_pretrained("model_name")
tokenizer = AutoTokenizer.from_pretrained("model_name")

# Inference
inputs = tokenizer("Hello world", return_tensors="pt")
outputs = model(**inputs)
```

---

## ✅ Status

**Installation:** ✅ Added to Dockerfile  
**Version:** Latest stable (2.5.1+)  
**Type:** CPU-only (default)  
**Mirror support:** ✅ Yes  
**Cache enabled:** ✅ Yes  

Ready to build! 🚀
