import os
from PIL import Image
from torch.utils.data import Dataset

class DeepfakeDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.samples = []
        self.transform = transform

        if not os.path.exists(root_dir):
            raise FileNotFoundError(f"Dataset not found: {root_dir}")

        label_map = {"real": 0, "fake": 1}

        for class_name, label in label_map.items():
            class_path = os.path.join(root_dir, class_name)

            if not os.path.exists(class_path):
                continue

            for img_name in sorted(os.listdir(class_path)):
                if img_name.lower().endswith((".jpg", ".png", ".jpeg")):
                    path = os.path.join(class_path, img_name)
                    self.samples.append((path, label))

        if len(self.samples) == 0:
            raise ValueError(f"No data found in {root_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]

        image = Image.open(path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, label