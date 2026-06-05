import os
import random
import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import transforms
from sklearn.metrics import accuracy_score, f1_score

from dataset import DeepfakeDataset
from model import DeepfakeViT
from utils import EarlyStopping

# ===============================================================
# LOGGING
# ===============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ===============================================================
# REPRODUCIBILITY
# ===============================================================
def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ===============================================================
# CONFIG
# ===============================================================
SEED        = 42
BATCH_SIZE  = 16        # effective = BATCH_SIZE × GRAD_ACCUM_STEPS
GRAD_ACCUM_STEPS = 4    # effective batch size = 64
EPOCHS      = 20        # more epochs; early stopping will halt if needed

# Two-phase LRs
HEAD_LR     = 1e-3      # Phase 1: head warmup
BACKBONE_LR = 1e-5      # Phase 2: full fine-tune

WEIGHT_DECAY   = 0.01
PATIENCE       = 5       # increased — gives scheduler time to recover
WARMUP_EPOCHS  = 5       # Phase 1 duration (head only)
DROPOUT        = 0.3
MAX_GRAD_NORM  = 1.0     # gradient clipping — prevents ViT gradient spikes

# DataLoader
NUM_WORKERS    = min(4, os.cpu_count() or 2)
PREFETCH       = 2

BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_model.pth")
LOG_PATH   = os.path.join(BASE_DIR, "models", "training_log.csv")


# ===============================================================
# TRANSFORMS
# ===============================================================
# HuggingFace ViT-B/16 pretrained with mean=0.5, std=0.5
IMAGENET_MEAN = [0.5, 0.5, 0.5]
IMAGENET_STD  = [0.5, 0.5, 0.5]

train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    # ── Spatial augmentations ─────────────────────────────────
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.2),
    transforms.RandomAffine(
        degrees=10,
        translate=(0.05, 0.05),
    ),
    # ── Color / quality augmentations ─────────────────────────
    transforms.ColorJitter(
        brightness=0.2,
        contrast=0.2,
        saturation=0.1,
        hue=0.05,
    ),
    transforms.RandomGrayscale(p=0.05),
    # ── Simulate real-world degradation ───────────────────────
    # GaussianBlur: simulates social media / messaging compression
    transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
    # ── To tensor + normalize ─────────────────────────────────
    transforms.ToTensor(),
    # RandomErasing: simulates occlusions and watermarks
    transforms.RandomErasing(p=0.15, scale=(0.02, 0.15)),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
])


# ===============================================================
# METRICS HELPER
# ===============================================================
def compute_metrics(all_labels, all_preds):
    """Compute accuracy and F1 from collected labels and predictions."""
    acc = accuracy_score(all_labels, all_preds)
    f1  = f1_score(all_labels, all_preds, zero_division=0)
    return acc, f1


# ===============================================================
# MAIN TRAINING FUNCTION
# ===============================================================
def train():
    set_seed(SEED)

    device   = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    logger.info(f"Training on: {device}")

    if use_cuda:
        # benchmark=True is safe for ViT (fixed input size 224×224)
        # deterministic=False allows cuDNN to pick fastest algorithm
        torch.backends.cudnn.benchmark = True

    # ── Data ──────────────────────────────────────────────────
    train_path = os.path.join(BASE_DIR, "datasets", "train")
    val_path   = os.path.join(BASE_DIR, "datasets", "validation")

    logger.info(f"Train path : {train_path}")
    logger.info(f"Val path   : {val_path}")

    train_dataset = DeepfakeDataset(
        train_path, transform=train_transform, verbose=True
    )
    val_dataset = DeepfakeDataset(
        val_path, transform=val_transform, verbose=True
    )

    # ── Class-balanced sampler ─────────────────────────────────
    # Handles imbalance without modifying the loss function
    sample_weights = train_dataset.get_sampler_weights()
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        sampler=sampler,                  # replaces shuffle=True
        num_workers=NUM_WORKERS,
        pin_memory=use_cuda,
        persistent_workers=True,
        prefetch_factor=PREFETCH,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=use_cuda,
        persistent_workers=True,
        prefetch_factor=PREFETCH,
    )

    logger.info(f"Train batches : {len(train_loader)}")
    logger.info(f"Val batches   : {len(val_loader)}")
    logger.info(
        f"Effective batch size: {BATCH_SIZE} × {GRAD_ACCUM_STEPS} = "
        f"{BATCH_SIZE * GRAD_ACCUM_STEPS}"
    )

    # ── Model ─────────────────────────────────────────────────
    model = DeepfakeViT(pretrained=True, dropout=DROPOUT).to(device)
    logger.info(f"\n{model}\n")

    # ── Loss ──────────────────────────────────────────────────
    # Class weights in loss as secondary imbalance safeguard
    class_weights = train_dataset.get_class_weights().to(device)
    pos_weight = class_weights[1] / class_weights[0]  # fake weight / real weight
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    # ── Phase 1 optimizer: head only ──────────────────────────
    model.freeze_backbone()
    optimizer = torch.optim.AdamW(
        model.classifier.parameters(),
        lr=HEAD_LR,
        weight_decay=WEIGHT_DECAY
    )

    # Cosine annealing over total epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=EPOCHS,
        eta_min=1e-7
    )

    # ── Mixed precision ───────────────────────────────────────
    scaler = torch.amp.GradScaler("cuda") if use_cuda else None

    # ── Early stopping ────────────────────────────────────────
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    early_stopping = EarlyStopping(
        patience=PATIENCE,
        min_delta=1e-4,
        save_path=MODEL_PATH,
        verbose=True,
    )

    # ── Training log ─────────────────────────────────────────
    history = []

    # ══════════════════════════════════════════════════════════
    # EPOCH LOOP
    # ══════════════════════════════════════════════════════════
    for epoch in range(1, EPOCHS + 1):

        # ── Phase transition at warmup boundary ───────────────
        if epoch == WARMUP_EPOCHS + 1:
            logger.info("\n🔓 Phase 2: Unfreezing backbone for full fine-tuning...")
            model.unfreeze_last_n_layers(n=4)   # unfreeze last 4 layers first
            optimizer = torch.optim.AdamW(
                model.get_param_groups(
                    head_lr=HEAD_LR / 10,
                    backbone_lr=BACKBONE_LR
                ),
                weight_decay=WEIGHT_DECAY
            )
            # Reset scheduler for phase 2
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=EPOCHS - WARMUP_EPOCHS,
                eta_min=1e-7
            )

        # ── Train loop ────────────────────────────────────────
        model.train()
        train_loss   = 0.0
        train_labels = []
        train_preds  = []

        optimizer.zero_grad()  # zero once before accumulation loop

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True).unsqueeze(1).float()

            if scaler is not None:
                with torch.amp.autocast("cuda"):
                    outputs = model(images)
                    loss    = criterion(outputs, labels) / GRAD_ACCUM_STEPS
                scaler.scale(loss).backward()

                if (batch_idx + 1) % GRAD_ACCUM_STEPS == 0 or (batch_idx + 1) == len(train_loader):
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                    scaler.step(optimizer)
                    scaler.update()
                    optimizer.zero_grad()
            else:
                # CPU fallback (no autocast)
                outputs = model(images)
                loss    = criterion(outputs, labels) / GRAD_ACCUM_STEPS
                loss.backward()

                if (batch_idx + 1) % GRAD_ACCUM_STEPS == 0 or (batch_idx + 1) == len(train_loader):
                    torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                    optimizer.step()
                    optimizer.zero_grad()

             # Undo the /GRAD_ACCUM_STEPS for accurate loss tracking
            train_loss += loss.item() * GRAD_ACCUM_STEPS

            # Collect predictions for metrics
            preds = (torch.sigmoid(outputs) > 0.5).long().squeeze(1)
            train_labels.extend(labels.squeeze(1).long().cpu().numpy())
            train_preds.extend(preds.cpu().numpy())

        train_loss /= len(train_loader)
        train_acc, train_f1 = compute_metrics(train_labels, train_preds)

        # ── Validation loop ───────────────────────────────────
        model.eval()
        val_loss   = 0.0
        val_labels = []
        val_preds  = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True).unsqueeze(1).float()

                if scaler is not None:
                    with torch.amp.autocast("cuda"):
                        outputs = model(images)
                        loss    = criterion(outputs, labels)
                else:
                    outputs = model(images)
                    loss    = criterion(outputs, labels)

                val_loss += loss.item()

                preds = (torch.sigmoid(outputs) > 0.5).long().squeeze(1)
                val_labels.extend(labels.squeeze(1).long().cpu().numpy())
                val_preds.extend(preds.cpu().numpy())

        val_loss /= len(val_loader)
        val_acc, val_f1 = compute_metrics(val_labels, val_preds)

        scheduler.step()

        # ── Logging ───────────────────────────────────────────
        current_lr = scheduler.get_last_lr()[0]
        logger.info(
            f"Epoch {epoch:02d}/{EPOCHS} | "
            f"LR: {current_lr:.2e} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} F1: {train_f1:.4f} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} F1: {val_f1:.4f}"
        )

        history.append({
            "epoch": epoch, "lr": current_lr,
            "train_loss": train_loss, "train_acc": train_acc, "train_f1": train_f1,
            "val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1,
        })

        # ── Early stopping + checkpoint ───────────────────────
        early_stopping(
            val_acc=val_acc,
            model=model,
            optimizer=optimizer,
            epoch=epoch,
            extra={"val_f1": val_f1, "val_loss": val_loss},
        )

        if early_stopping.early_stop:
            logger.info("🛑 Early stopping triggered.")
            break

    # ── Save training history ─────────────────────────────────
    _save_history(history, LOG_PATH)
    logger.info(f"\nTraining complete. Best val_acc: {early_stopping.best_acc:.4f}")
    logger.info(f"Model saved at : {MODEL_PATH}")
    logger.info(f"Training log   : {LOG_PATH}")


# ===============================================================
# SAVE HISTORY
# ===============================================================
def _save_history(history: list, path: str):
    """Save training history to CSV for later plotting."""
    import csv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not history:
        return
    keys = history[0].keys()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(history)
    logger.info(f"Training log saved to: {path}")


# ===============================================================
# ENTRY POINT
# ===============================================================
if __name__ == "__main__":
    train()