import os
import time
import logging
import torch
import numpy as np
from torch.utils.data import DataLoader
from torchvision import transforms

from dataset import DeepfakeDataset
from model import DeepfakeViT
from utils import calculate_metrics, print_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ===============================================================
# CONFIG
# ===============================================================
BATCH_SIZE = 16
NUM_WORKERS = 2

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PATH   = os.path.join(BASE_DIR, "datasets", "test")
MODEL_PATH  = os.path.join(BASE_DIR, "models", "best_model.pth")

# Must match training normalization exactly
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])


# ===============================================================
# LOAD MODEL — handles both old and new checkpoint formats
# ===============================================================
def load_model(model_path: str, device: torch.device) -> DeepfakeViT:
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

    model = DeepfakeViT(pretrained=False).to(device)

    checkpoint = torch.load(model_path, map_location=device, weights_only=True)

    # Handle both formats:
    # - new format: {"model_state_dict": ..., "epoch": ..., ...}
    # - old format: raw state_dict
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        epoch   = checkpoint.get("epoch", "?")
        val_acc = checkpoint.get("val_acc", "?")
        val_f1  = checkpoint.get("val_f1", "?")
        logger.info(
            f"Loaded checkpoint — epoch: {epoch} | "
            f"val_acc: {val_acc} | val_f1: {val_f1}"
        )
    else:
        # Legacy: raw state dict
        model.load_state_dict(checkpoint)
        logger.warning("Loaded legacy checkpoint (raw state_dict). No metadata available.")

    model.eval()
    return model


# ===============================================================
# EVALUATE
# ===============================================================
def evaluate(model_path: str = MODEL_PATH, test_path: str = TEST_PATH):
    device   = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    logger.info(f"Evaluating on: {device}")

    # ── Dataset ───────────────────────────────────────────────
    test_dataset = DeepfakeDataset(test_path, transform=transform, verbose=True)

    if len(test_dataset) == 0:
        raise ValueError(f"No test images found at: {test_path}")

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=use_cuda,
    )

    # ── Model ─────────────────────────────────────────────────
    model = load_model(model_path, device)

    # ── Inference ─────────────────────────────────────────────
    all_labels = []
    all_probs  = []

    start_time = time.time()

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device, non_blocking=True)

            if use_cuda:
                with torch.amp.autocast("cuda"):
                    outputs = model(images)
            else:
                outputs = model(images)

            # Convert logits → probabilities
            probs = torch.sigmoid(outputs).squeeze(1)

            all_probs.extend(probs.cpu().numpy())
            all_labels.extend(labels.numpy())

    elapsed      = time.time() - start_time
    total        = len(all_labels)
    time_per_img = (elapsed / total) * 1000  # ms

    logger.info(
        f"Inference complete: {total} images in "
        f"{elapsed:.2f}s ({time_per_img:.2f} ms/image)"
    )

    # ── Metrics ───────────────────────────────────────────────
    metrics = calculate_metrics(
        y_true=all_labels,
        y_pred_probs=all_probs
    )
    print_metrics(metrics, split="Test")

    return metrics


# ===============================================================
# ENTRY POINT
# ===============================================================
if __name__ == "__main__":
    evaluate()