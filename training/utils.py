import torch
import numpy as np
import logging
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix
)

logger = logging.getLogger(__name__)

# ── Threshold (single source of truth) ──────────────────────────────
DECISION_THRESHOLD = 0.5


def calculate_metrics(y_true, y_pred_probs, threshold: float = DECISION_THRESHOLD):
    """
    Compute full binary classification metrics.

    Args:
        y_true       : list or array of ground truth labels (0/1)
        y_pred_probs : list or array of predicted probabilities (after sigmoid)
        threshold    : decision boundary (default 0.5)

    Returns:
        dict with keys: acc, precision, recall, f1, auc, confusion_matrix
    """
    y_true        = np.array(y_true)
    y_pred_probs  = np.array(y_pred_probs)
    y_pred        = (y_pred_probs >= threshold).astype(int)

    acc  = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec  = recall_score(y_true, y_pred, zero_division=0)
    f1   = f1_score(y_true, y_pred, zero_division=0)
    cm   = confusion_matrix(y_true, y_pred)

    try:
        auc = roc_auc_score(y_true, y_pred_probs)
    except ValueError:
        # Only one class present in y_true (degenerate split)
        logger.warning("ROC-AUC undefined: only one class in y_true. Defaulting to 0.5.")
        auc = 0.5

    return {
        "acc":              acc,
        "precision":        prec,
        "recall":           rec,
        "f1":               f1,
        "auc":              auc,
        "confusion_matrix": cm,
    }


def print_metrics(metrics: dict, split: str = "Test"):
    """Pretty-print the metrics dict returned by calculate_metrics."""
    cm = metrics["confusion_matrix"]

    # Safely extract confusion matrix values
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn = fp = fn = tp = 0

    print(f"\n{'='*45}")
    print(f"  {split} Results")
    print(f"{'='*45}")
    print(f"  Accuracy  : {metrics['acc']  * 100:.2f}%")
    print(f"  Precision : {metrics['precision'] * 100:.2f}%")
    print(f"  Recall    : {metrics['recall']    * 100:.2f}%")
    print(f"  F1 Score  : {metrics['f1']        * 100:.2f}%")
    print(f"  ROC-AUC   : {metrics['auc']:.4f}")
    print(f"\n  Confusion Matrix:")
    print(f"             Pred REAL  Pred FAKE")
    print(f"  True REAL :   {tn:>6}     {fp:>6}")
    print(f"  True FAKE :   {fn:>6}     {tp:>6}")
    print(f"\n  True Positives  (Fake→Fake) : {tp}")
    print(f"  True Negatives  (Real→Real) : {tn}")
    print(f"  False Positives (Real→Fake) : {fp}  ← real wrongly flagged")
    print(f"  False Negatives (Fake→Real) : {fn}  ← fake missed")
    print(f"{'='*45}\n")


class EarlyStopping:
    """
    Monitors validation accuracy (higher = better).
    Saves full checkpoint — compatible with improved train.py format.

    Args:
        patience   : epochs to wait after last improvement
        min_delta  : minimum improvement to count as progress
        save_path  : where to save the best checkpoint
        verbose    : print status each epoch
    """

    def __init__(
        self,
        patience:  int   = 5,
        min_delta: float = 1e-4,
        save_path: str   = "models/best_model.pth",
        verbose:   bool  = True,
    ):
        self.patience   = patience
        self.min_delta  = min_delta
        self.save_path  = save_path
        self.verbose    = verbose

        self.counter    = 0
        self.best_acc   = 0.0
        self.early_stop = False

    def __call__(self, val_acc: float, model, optimizer=None, epoch: int = 0, extra: dict = None):
        """
        Call once per epoch.

        Args:
            val_acc   : validation accuracy for this epoch
            model     : the model (for saving state_dict)
            optimizer : optional optimizer (for full checkpoint)
            epoch     : current epoch number
            extra     : optional dict of extra keys to save (val_loss, val_f1, etc.)
        """
        if val_acc > self.best_acc + self.min_delta:
            self.best_acc = val_acc
            self.counter  = 0
            self._save_checkpoint(model, optimizer, epoch, val_acc, extra)
        else:
            self.counter += 1
            if self.verbose:
                logger.info(
                    f"EarlyStopping: no improvement "
                    f"({self.counter}/{self.patience}) | "
                    f"best_acc={self.best_acc:.4f}"
                )
            if self.counter >= self.patience:
                self.early_stop = True

    def _save_checkpoint(self, model, optimizer, epoch, val_acc, extra):
        """Save full training checkpoint."""
        import os
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

        checkpoint = {
            "epoch":            epoch,
            "model_state_dict": model.state_dict(),
            "val_acc":          val_acc,
        }
        if optimizer is not None:
            checkpoint["optimizer_state_dict"] = optimizer.state_dict()
        if extra:
            checkpoint.update(extra)

        torch.save(checkpoint, self.save_path)

        if self.verbose:
            logger.info(
                f"  ✅ Checkpoint saved (val_acc={val_acc:.4f}) → {self.save_path}"
            )