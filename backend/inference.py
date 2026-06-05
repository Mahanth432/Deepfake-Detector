import os
import sys
import torch
from PIL import Image
import logging
from torchvision import transforms

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add training folder to path so we can import the shared model class
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'training'))
from model import DeepfakeViT


class DeepfakeDetector:
    """
    Image-only deepfake detector.

    Uses the same DeepfakeViT model class as training/test pipelines.
    Model outputs raw logits → sigmoid applied here to get probability.

    Label convention:
        REAL = 0  (prob < 0.5)
        FAKE = 1  (prob >= 0.5)
    """

    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'models',
                'best_model.pth',
            )

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.model = DeepfakeViT(pretrained=False).to(self.device)
        self.model.eval()
        self.model_loaded = False

        if os.path.exists(model_path):
            try:
                self.model.load_state_dict(
                    torch.load(model_path, map_location=self.device)
                )
                self.model_loaded = True
                logger.info(f"ViT model loaded from: {model_path}")
            except Exception as e:
                logger.error(f"Error loading model from {model_path}: {e}")
        else:
            logger.warning(
                f"Model file not found at '{model_path}'. "
                "Predictions are disabled until a trained model is available."
            )

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.5, 0.5, 0.5],
                std=[0.5, 0.5, 0.5],
            ),
        ])

    def preprocess_image(self, image_np):
        """
        Accepts an RGB numpy array.
        Returns a (1, 3, 224, 224) tensor on the correct device.
        """
        try:
            pil_img    = Image.fromarray(image_np).convert("RGB")
            tensor_img = self.transform(pil_img).unsqueeze(0).to(self.device)
            return tensor_img
        except Exception as e:
            logger.error(f"Error in preprocess_image: {e}")
            return None

    def predict_image(self, image_np):
        """
        Accepts an RGB numpy array image.

        Returns:
            label       (str)  – 'Real' or 'Fake'
            probability (float)– probability of Fake class [0, 1]
        """
        tensor_img = self.preprocess_image(image_np)

        if not self.model_loaded:
            raise RuntimeError("Model is not loaded. Train and save models/best_model.pth first.")

        if tensor_img is None:
            return "UNKNOWN", 0.0

        with torch.no_grad():
            logits = self.model(tensor_img)          # raw logit
            prob_fake = torch.sigmoid(logits).item()
        prob_real = 1 - prob_fake

        label = "Fake" if prob_fake >= 0.5 else "Real"

        confidence = prob_fake if label == "Fake" else prob_real

        return label, confidence

# Module-level singleton used by backend/app.py
detector = DeepfakeDetector()