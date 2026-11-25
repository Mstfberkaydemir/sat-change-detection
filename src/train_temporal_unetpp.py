import os, glob
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import segmentation_models_pytorch as smp

class TemporalBuildingDataset(Dataset):
    def __init__(self, folder, augment=False):
        self.files = sorted(glob.glob(os.path.join(folder, "*.npz")))
        self.augment = augment

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        d = np.load(self.files[idx])
        t1 = d["t1"].astype(np.float32) / 255.0
        t2 = d["t2"].astype(np.float32) / 255.0
        m1 = d["m1"].astype(np.float32)
        m2 = d["m2"].astype(np.float32)
        chg = d["chg"].astype(np.float32)

        if self.augment:
            if np.random.rand() > 0.5:
                t1, t2 = np.fliplr(t1).copy(), np.fliplr(t2).copy()
                m1, m2, chg = np.fliplr(m1).copy(), np.fliplr(m2).copy(), np.fliplr(chg).copy()
            if np.random.rand() > 0.5:
                t1, t2 = np.flipud(t1).copy(), np.flipud(t2).copy()
                m1, m2, chg = np.flipud(m1).copy(), np.flipud(m2).copy(), np.flipud(chg).copy()

        x = np.concatenate([t1, t2], axis=-1)
        x_t = torch.tensor(x).permute(2, 0, 1)
        y_t = torch.stack([torch.tensor(m1), torch.tensor(m2), torch.tensor(chg)], dim=0)
        return x_t, y_t

def get_model():
    return smp.UnetPlusPlus(
        encoder_name="resnet34",
        encoder_weights="imagenet",
        in_channels=6,
        classes=3
    )
