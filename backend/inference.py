import os
import sys
import time
import logging
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Path resolution (robust for deployment) ─────────────────────────
BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
TRAINING_DIR = os.path.join(PROJECT_ROOT, "training")

if TRAINING_DIR not in sys.path:
    sys.path.insert(0, TRAINING_DIR)

from model import DeepfakeViT


# ── Preprocessing transform (matches training exactly) ──────────────
INFERENCE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])


class DeepfakeDetector:
    """
    Production inference wrapper for DeepfakeViT.

    Label convention  : REAL = 0  |  FAKE = 1
    Output convention : always returns prob_fake in [0, 1]
                        label is derived from prob_fake >= threshold

    Usage:
        detector = DeepfakeDetector()
        label, prob_fake, confidence = detector.predict_image(image_np)
    """

    DEFAULT_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "best_model.pth")
    THRESHOLD = 0.5

    def __init__(self, model_path: str = None, threshold: float = None):
        self.model_path   = model_path or self.DEFAULT_MODEL_PATH
        self.threshold    = threshold  or self.THRESHOLD
        self.device       = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_cuda     = self.device.type == "cuda"
        self.model        = None
        self.model_loaded = False

        self._load_model()

    # ----------------------------------------------------------------
    # Model loading
    # ----------------------------------------------------------------

    def _load_model(self):
        """
        Load model weights from checkpoint.
        Handles both new format (dict with model_state_dict)
        and legacy format (raw state_dict).
        """
        if not os.path.exists(self.model_path):
            logger.warning(
                f"Model not found at: {self.model_path}\n"
                "Predictions disabled until best_model.pth is available."
            )
            return

        try:
            model = DeepfakeViT(pretrained=False).to(self.device)

            checkpoint = torch.load(
                self.model_path,
                map_location=self.device,
                weights_only=True      # safe loading — no arbitrary code execution
            )

            # Handle both checkpoint formats
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
                epoch   = checkpoint.get("epoch", "?")
                val_acc = checkpoint.get("val_acc", "?")
                logger.info(
                    f"Loaded checkpoint — epoch: {epoch} | val_acc: {val_acc}"
                )
            else:
                # Legacy: raw state_dict
                model.load_state_dict(checkpoint)
                logger.warning("Loaded legacy checkpoint (raw state_dict).")

            # eval() AFTER load_state_dict
            model.eval()

            self.model        = model
            self.model_loaded = True
            logger.info(f"Model ready on {self.device} | threshold={self.threshold}")

        except Exception as e:
            logger.error(f"Failed to load model from {self.model_path}: {e}")
            self.model_loaded = False

    # ----------------------------------------------------------------
    # Preprocessing
    # ----------------------------------------------------------------

    def _preprocess(self, image_np: np.ndarray) -> torch.Tensor:
        """
        Convert numpy RGB array → (1, 3, 224, 224) tensor on device.

        Args:
            image_np: HxWx3 uint8 numpy array (RGB)

        Returns:
            tensor on self.device
        """
        if not isinstance(image_np, np.ndarray):
            raise TypeError(
                f"Expected numpy array, got {type(image_np).__name__}"
            )

        if image_np.ndim == 2:
            # Grayscale → replicate to 3 channels
            image_np = np.stack([image_np] * 3, axis=-1)
        elif image_np.shape[2] == 4:
            # RGBA → RGB (drop alpha)
            image_np = image_np[:, :, :3]

        pil_img = Image.fromarray(image_np.astype(np.uint8)).convert("RGB")
        tensor  = INFERENCE_TRANSFORM(pil_img).unsqueeze(0)
        return tensor.to(self.device, non_blocking=self.use_cuda)

    # ----------------------------------------------------------------
    # Prediction
    # ----------------------------------------------------------------

    def predict_image(self, image_np: np.ndarray) -> dict:
        """
        Run inference on a single image.

        Args:
            image_np: HxWx3 uint8 numpy array (RGB)

        Returns:
            dict with keys:
                label      (str)   – 'Real' or 'Fake'
                prob_fake  (float) – probability of being AI-generated [0, 1]
                confidence (float) – probability of the predicted class [0, 1]
                inference_ms (float) – inference time in milliseconds
        """
        # ── Guard: model must be loaded first ───────────────────
        if not self.model_loaded:
            raise RuntimeError(
                "Model is not loaded. "
                "Run training and ensure models/best_model.pth exists."
            )

        # ── Preprocess ──────────────────────────────────────────
        try:
            tensor = self._preprocess(image_np)
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            raise ValueError(f"Image preprocessing failed: {e}") from e

        # ── Inference ───────────────────────────────────────────
        start = time.perf_counter()

        with torch.no_grad():
            if self.use_cuda:
                with torch.amp.autocast("cuda"):
                    logits = self.model(tensor)
            else:
                logits = self.model(tensor)

        inference_ms = (time.perf_counter() - start) * 1000

        # ── Post-process ────────────────────────────────────────
        prob_fake  = torch.sigmoid(logits).item()   # always fakeness score
        prob_real  = 1.0 - prob_fake
        is_fake    = prob_fake >= self.threshold

        label      = "Fake" if is_fake else "Real"
        confidence = prob_fake if is_fake else prob_real

        logger.info(
            f"Prediction: {label} | "
            f"prob_fake={prob_fake:.4f} | "
            f"confidence={confidence:.4f} | "
            f"{inference_ms:.1f}ms"
        )

        return {
            "label":        label,
            "prob_fake":    round(prob_fake,  4),
            "confidence":   round(confidence, 4),
            "inference_ms": round(inference_ms, 2),
        }

    # ----------------------------------------------------------------
    # Status
    # ----------------------------------------------------------------

    def is_ready(self) -> bool:
        """Check if model is loaded and ready for inference."""
        return self.model_loaded

    def get_status(self) -> dict:
        """
        Return detector status — useful for a /health API endpoint.

        Usage in app.py:
            @app.route("/health")
            def health():
                return jsonify(detector.get_status())
        """
        return {
            "model_loaded": self.model_loaded,
            "device":       str(self.device),
            "threshold":    self.threshold,
            "model_path":   self.model_path,
        }

    def __repr__(self) -> str:
        return (
            f"DeepfakeDetector("
            f"loaded={self.model_loaded}, "
            f"device={self.device}, "
            f"threshold={self.threshold})"
        )


# ── Module-level singleton ───────────────────────────────────────────
# Loaded once when app.py imports this module.
# If model is missing, detector.model_loaded = False (app still starts).
detector = DeepfakeDetector()