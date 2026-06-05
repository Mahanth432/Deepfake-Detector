import os
import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from dataset import DeepfakeDataset
from model import DeepfakeViT

# ================= ROOT PATH =================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_model.pth")

# ================= CONFIG =================
BATCH_SIZE = 16
EPOCHS = 10
LR = 1e-4
PATIENCE = 3

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Training on:", device)

# ================= TRANSFORM =================
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])

# ================= DATA =================
train_path = os.path.join(BASE_DIR, "datasets", "train")
val_path = os.path.join(BASE_DIR, "datasets", "validation")

print("Train path:", train_path)
print("Val path:", val_path)

train_dataset = DeepfakeDataset(train_path, transform=transform)
val_dataset = DeepfakeDataset(val_path, transform=transform)

print("Train samples:", len(train_dataset))
print("Val samples:", len(val_dataset))

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)

# ================= MODEL =================
model = DeepfakeViT().to(device)

criterion = torch.nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LR)

scaler = torch.amp.GradScaler("cuda")

# ================= EARLY STOP =================
best_val = float("inf")
counter = 0

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

# ================= TRAIN =================
for epoch in range(EPOCHS):
    print(f"\nEpoch {epoch+1}/{EPOCHS}")

    model.train()
    train_loss = 0

    for images, labels in train_loader:
        images = images.to(device)
        labels = labels.to(device).unsqueeze(1).float()

        optimizer.zero_grad()

        with torch.amp.autocast("cuda"):
            outputs = model(images)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        train_loss += loss.item()

    train_loss /= len(train_loader)

    # ================= VALIDATION =================
    model.eval()
    val_loss = 0

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device).unsqueeze(1).float()

            with torch.amp.autocast("cuda"):
                outputs = model(images)
                loss = criterion(outputs, labels)

            val_loss += loss.item()

    val_loss /= len(val_loader)

    print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

    # ================= SAVE BEST =================
    if val_loss < best_val:
        best_val = val_loss
        counter = 0

        torch.save(model.state_dict(), MODEL_PATH)
        print("✅ Saved best model at:", MODEL_PATH)

    else:
        counter += 1
        print(f"No improvement ({counter}/{PATIENCE})")

    if counter >= PATIENCE:
        print("🛑 Early stopping triggered")
        break

print("Training complete ✅")