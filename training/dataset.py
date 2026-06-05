import os
import logging
import torch
import numpy as np
from PIL import Image
from torch.utils.data import Dataset
from collections import Counter

logger = logging.getLogger(__name__)


class DeepfakeDataset(Dataset):
    """
    Binary image dataset for deepfake detection.

    Label convention:
        real = 0
        fake = 1

    Expects directory structure:
        root_dir/
        ├── real/   (authentic images)
        └── fake/   (AI-generated images)

    Features:
        - Corrupt image handling (skips bad files, logs warnings)
        - Class distribution logging
        - WeightedRandomSampler support via get_sampler_weights()
        - BCEWithLogitsLoss pos_weight support via get_class_weights()
    """

    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    LABEL_MAP = {"real": 0, "fake": 1}

    def __init__(self, root_dir: str, transform=None, verbose: bool = False):
        self.root_dir  = root_dir
        self.transform = transform
        self.samples   = []       # list of (path, label)
        self._labels   = []       # parallel list of labels for fast access

        if not os.path.exists(root_dir):
            raise FileNotFoundError(f"Dataset not found: {root_dir}")

        # ── Scan directories ────────────────────────────────────────
        for class_name, label in self.LABEL_MAP.items():
            class_path = os.path.join(root_dir, class_name)

            if not os.path.exists(class_path):
                if verbose:
                    logger.warning(f"Class directory missing: {class_path}")
                continue

            for img_name in sorted(os.listdir(class_path)):
                if img_name.lower().endswith(self.SUPPORTED_EXTENSIONS):
                    path = os.path.join(class_path, img_name)
                    self.samples.append((path, label))
                    self._labels.append(label)

        if len(self.samples) == 0:
            raise ValueError(f"No images found in {root_dir}")

        # ── Class distribution ──────────────────────────────────────
        self._class_counts = Counter(self._labels)
        self._num_real = self._class_counts.get(0, 0)
        self._num_fake = self._class_counts.get(1, 0)

        if verbose:
            total = len(self.samples)
            logger.info(
                f"Dataset loaded: {root_dir}\n"
                f"  Total  : {total:,}\n"
                f"  Real   : {self._num_real:,} ({100 * self._num_real / total:.1f}%)\n"
                f"  Fake   : {self._num_fake:,} ({100 * self._num_fake / total:.1f}%)"
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]

        try:
            image = Image.open(path).convert("RGB")
        except Exception as e:
            # ── Corrupt image fallback ───────────────────────────────
            # Log the bad file and return the next valid sample.
            # This prevents DataLoader worker crashes on large datasets.
            logger.warning(f"Corrupt image skipped: {path} — {e}")
            return self.__getitem__((idx + 1) % len(self.samples))

        if self.transform:
            image = self.transform(image)

        return image, label

    # ------------------------------------------------------------------
    # Sampler & loss helpers (called by train.py)
    # ------------------------------------------------------------------

    def get_sampler_weights(self) -> list:
        """
        Per-sample weights for WeightedRandomSampler.
        Inverse of class frequency — minority class gets higher weight.

        Usage:
            sampler = WeightedRandomSampler(
                weights=dataset.get_sampler_weights(),
                num_samples=len(dataset),
                replacement=True,
            )
        """
        total = len(self.samples)
        class_weights = {
            cls: total / count
            for cls, count in self._class_counts.items()
        }
        return [class_weights[label] for label in self._labels]

    def get_class_weights(self) -> torch.Tensor:
        """
        Class weights tensor for loss function (BCEWithLogitsLoss pos_weight).

        Returns:
            Tensor of shape (2,) with weights [weight_real, weight_fake]

        Usage in train.py:
            weights = dataset.get_class_weights()
            pos_weight = weights[1] / weights[0]
            criterion = BCEWithLogitsLoss(pos_weight=pos_weight)
        """
        total = len(self.samples)
        num_classes = 2
        weights = torch.zeros(num_classes)

        for cls, count in self._class_counts.items():
            # Inverse frequency, normalized
            weights[cls] = total / (num_classes * count) if count > 0 else 1.0

        return weights

    @property
    def class_counts(self) -> dict:
        """Returns {0: num_real, 1: num_fake}."""
        return dict(self._class_counts)