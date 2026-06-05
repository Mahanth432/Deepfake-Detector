import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from dataset import DeepfakeDataset
from model import DeepfakeViT
import os

# ===== CONFIG =====
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Device:", device)

# ===== TRANSFORM =====
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
])

# ===== PATHS =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
test_path = os.path.join(BASE_DIR, "datasets", "test")
model_path = os.path.join(BASE_DIR, "models", "best_model.pth")

# ===== DATASET =====
test_dataset = DeepfakeDataset(test_path, transform=transform)

print("Test path:", os.path.abspath(test_path))
print("Test samples:", len(test_dataset))
print("Model path:", model_path)

if len(test_dataset) == 0:
    print("❌ ERROR: No test images found. Check folder structure!")
    exit()

# ===== DATALOADER =====
test_loader = DataLoader(
    test_dataset,
    batch_size=16,
    shuffle=False
)

# ===== MODEL =====
model = DeepfakeViT().to(device)
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Trained model not found: {model_path}")
model.load_state_dict(torch.load(model_path, map_location=device))
model.eval()

# ===== EVALUATION =====
correct = 0
total = 0

with torch.no_grad():
    for images, labels in test_loader:
        images = images.to(device)
        labels = labels.to(device).unsqueeze(1)

        outputs = model(images)

        preds = torch.sigmoid(outputs)
        preds = (preds > 0.5).float()

        correct += (preds == labels).sum().item()
        total += labels.size(0)

# ===== SAFE DIVISION =====
if total == 0:
    print("❌ No samples processed!")
else:
    accuracy = correct / total
    print(f"\n🔥 Test Accuracy: {accuracy * 100:.2f}%")