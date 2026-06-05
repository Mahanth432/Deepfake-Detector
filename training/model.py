import torch
import torch.nn as nn
from transformers import ViTConfig, ViTModel
import logging

logger = logging.getLogger(__name__)


class DeepfakeViT(nn.Module):
    """
    Binary classifier: REAL (0) vs AI-GENERATED / FAKE (1)
    Backbone: google/vit-base-patch16-224-in21k

    Training strategy (two-phase):
        Phase 1 — Head warmup (epochs 1-5):
            model.freeze_backbone()
            optimizer = AdamW(model.classifier.parameters(), lr=1e-3)

        Phase 2 — Full fine-tune (epochs 6+):
            model.unfreeze_backbone()
            optimizer = AdamW(model.parameters(), lr=1e-5)

    Loss : BCEWithLogitsLoss  (do NOT sigmoid before loss)
    Infer: torch.sigmoid(model(x)) > 0.5  ->  fake
    """

    def __init__(self, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()

        # ── Backbone ────────────────────────────────────────────────
        if pretrained:
            logger.info("Loading pretrained ViT-B/16 (google/vit-base-patch16-224-in21k)...")
            self.backbone = ViTModel.from_pretrained(
                "google/vit-base-patch16-224-in21k"
            )
        else:
            logger.info("Initializing ViT-B/16 from scratch (no pretrained weights)...")
            self.backbone = ViTModel(ViTConfig())

        # Read hidden size dynamically — works for ViT-Small / Base / Large
        hidden_size = self.backbone.config.hidden_size  # 768 for ViT-B

        # ── Classification Head ──────────────────────────────────────
        # MLP head: CLS token -> 256 -> 1
        # Dropout prevents overfitting on the frozen backbone features
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 1)
        )

        # ── Weight init for classifier ───────────────────────────────
        self._init_classifier_weights()

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        """
        Args:
            pixel_values: (B, 3, 224, 224) — normalized ImageNet stats

        Returns:
            logits: (B, 1) — raw logits, no sigmoid
        """
        outputs = self.backbone(pixel_values=pixel_values)

        # CLS token: first token of last hidden state
        cls_token = outputs.last_hidden_state[:, 0]   # (B, hidden_size)

        logits = self.classifier(cls_token)            # (B, 1)

        return logits

    # ------------------------------------------------------------------
    # Freeze / Unfreeze helpers for two-phase training
    # ------------------------------------------------------------------

    def freeze_backbone(self):
        """
        Phase 1: Freeze all backbone parameters.
        Only the classification head will be trained.
        Use a high LR (1e-3) in this phase.
        """
        for param in self.backbone.parameters():
            param.requires_grad = False

        logger.info("Backbone FROZEN. Training classification head only.")
        self._log_trainable_params()

    def unfreeze_backbone(self):
        """
        Phase 2: Unfreeze all backbone parameters for full fine-tuning.
        Switch to a very low LR (1e-5) in this phase to avoid
        destroying pretrained representations.
        """
        for param in self.backbone.parameters():
            param.requires_grad = True

        logger.info("Backbone UNFROZEN. Full model fine-tuning enabled.")
        self._log_trainable_params()

    def unfreeze_last_n_layers(self, n: int = 4):
        """
        Partial unfreeze: only unfreeze the last n transformer encoder layers.
        Good middle ground between full freeze and full unfreeze.
        Recommended: start with n=4 before going to full unfreeze.

        ViT-B/16 has 12 encoder layers total.
        """
        # First freeze everything
        self.freeze_backbone()

        # Then selectively unfreeze last n encoder layers
        encoder_layers = self.backbone.encoder.layer
        total_layers = len(encoder_layers)
        unfreeze_from = max(0, total_layers - n)

        for i, layer in enumerate(encoder_layers):
            if i >= unfreeze_from:
                for param in layer.parameters():
                    param.requires_grad = True

        # Always unfreeze LayerNorm at the end of the backbone
        for param in self.backbone.layernorm.parameters():
            param.requires_grad = True

        logger.info(
            f"Partially unfrozen: last {n}/{total_layers} encoder layers + final LayerNorm."
        )
        self._log_trainable_params()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _init_classifier_weights(self):
        """Xavier init for linear layers in the classifier head (GELU activation)."""
        for module in self.classifier.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def _log_trainable_params(self):
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.parameters())
        logger.info(
            f"Trainable params: {trainable:,} / {total:,} "
            f"({100 * trainable / total:.1f}%)"
        )

    def get_param_groups(self, head_lr: float = 1e-3, backbone_lr: float = 1e-5):
        """
        Returns param groups with different LRs for backbone vs head.
        Use this when building the optimizer in train.py:

            optimizer = AdamW(model.get_param_groups(), weight_decay=0.01)

        This is better than a single LR for the entire model.
        """
        return [
            {
                "params": self.backbone.parameters(),
                "lr": backbone_lr,
                "name": "backbone"
            },
            {
                "params": self.classifier.parameters(),
                "lr": head_lr,
                "name": "classifier_head"
            },
        ]

    def __repr__(self) -> str:
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.parameters())
        return (
            f"DeepfakeViT(\n"
            f"  backbone : ViT-B/16 (google/vit-base-patch16-224-in21k)\n"
            f"  head     : Linear(768→256) → GELU → Dropout → Linear(256→1)\n"
            f"  trainable: {trainable:,} / {total:,} params\n"
            f")"
        )