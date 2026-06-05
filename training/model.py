import torch
import torch.nn as nn
from transformers import ViTConfig, ViTModel


class DeepfakeViT(nn.Module):
    """
    Binary deepfake classifier built on top of torchvision ViT-B/16.

    Output: raw logit (1 value).
    Do NOT apply sigmoid here — use BCEWithLogitsLoss during training.
    Apply torch.sigmoid(logits) during inference/testing to get probability.

    Label convention:
        REAL = 0
        FAKE = 1
    """

    def __init__(self, pretrained=True):
        super(DeepfakeViT, self).__init__()
        if pretrained:
            self.model = ViTModel.from_pretrained("google/vit-base-patch16-224-in21k")
        else:
            self.model = ViTModel(ViTConfig())
        self.classifier = nn.Linear(768, 1)

    def forward(self, x):
        outputs = self.model(pixel_values=x)
        cls_token = outputs.last_hidden_state[:, 0]
        logits = self.classifier(cls_token)
        return logits
