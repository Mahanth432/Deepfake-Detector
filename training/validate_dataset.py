"""
Dataset Validation Utility for GRAVEX-200K
==========================================

Run BEFORE training to catch problems early.

Checks:
    1. Corrupt / unreadable images
    2. Extremely small images (< 32×32)
    3. Class distribution per split
    4. File format breakdown
    5. Duplicate detection via SHA-256 hash
    6. Image dimension statistics

Usage:
    python validate_dataset.py                        # uses default path
    python validate_dataset.py --data-dir /path/to    # custom path
"""

import os
import sys
import hashlib
import argparse
import logging
from collections import Counter, defaultdict
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
MIN_DIMENSION = 32  # px


def scan_split(split_path: str, split_name: str) -> dict:
    """
    Scan a single split (train/validation/test) and return statistics.

    Returns dict with keys:
        total, per_class, corrupt, small, formats, dimensions, hashes
    """
    stats = {
        "total":      0,
        "per_class":  Counter(),
        "corrupt":    [],
        "small":      [],
        "formats":    Counter(),
        "widths":     [],
        "heights":    [],
        "hashes":     defaultdict(list),  # hash → [paths]
    }

    if not os.path.exists(split_path):
        logger.warning(f"Split directory not found: {split_path}")
        return stats

    for class_name in ["real", "fake"]:
        class_path = os.path.join(split_path, class_name)
        if not os.path.exists(class_path):
            logger.warning(f"  Class directory missing: {class_path}")
            continue

        files = sorted([
            f for f in os.listdir(class_path)
            if f.lower().endswith(SUPPORTED_EXTENSIONS)
        ])

        for fname in files:
            fpath = os.path.join(class_path, fname)
            stats["total"] += 1
            stats["per_class"][class_name] += 1

            # File extension
            ext = os.path.splitext(fname)[1].lower()
            stats["formats"][ext] += 1

            # File hash (for duplicate detection)
            try:
                with open(fpath, "rb") as fobj:
                    file_hash = hashlib.sha256(fobj.read()).hexdigest()
                stats["hashes"][file_hash].append(fpath)
            except Exception:
                pass  # hash failure is not critical

            # Image integrity check
            try:
                with Image.open(fpath) as img:
                    img.verify()  # fast check — doesn't load full pixels
                # Re-open after verify (verify closes the file)
                with Image.open(fpath) as img:
                    w, h = img.size
                    stats["widths"].append(w)
                    stats["heights"].append(h)
                    if w < MIN_DIMENSION or h < MIN_DIMENSION:
                        stats["small"].append((fpath, w, h))
            except Exception as e:
                stats["corrupt"].append((fpath, str(e)))

    return stats


def print_split_report(split_name: str, stats: dict):
    """Pretty-print the report for one split."""
    total = stats["total"]
    if total == 0:
        print(f"\n{'='*50}")
        print(f"  {split_name.upper()} — EMPTY (no images found)")
        print(f"{'='*50}")
        return

    print(f"\n{'='*50}")
    print(f"  {split_name.upper()} SPLIT")
    print(f"{'='*50}")

    # Class distribution
    print(f"\n  Total images: {total:,}")
    for cls in ["real", "fake"]:
        count = stats["per_class"].get(cls, 0)
        pct = 100 * count / total if total > 0 else 0
        print(f"    {cls:>5}: {count:>8,}  ({pct:.1f}%)")

    # Balance ratio
    real_count = stats["per_class"].get("real", 0)
    fake_count = stats["per_class"].get("fake", 0)
    if real_count > 0 and fake_count > 0:
        ratio = max(real_count, fake_count) / min(real_count, fake_count)
        balance = "✅ balanced" if ratio < 1.5 else f"⚠️ imbalanced ({ratio:.1f}:1)"
        print(f"    Ratio: {balance}")

    # File formats
    print(f"\n  File formats:")
    for ext, count in stats["formats"].most_common():
        print(f"    {ext:>6}: {count:>8,}")

    # Image dimensions
    if stats["widths"]:
        import numpy as np
        widths  = np.array(stats["widths"])
        heights = np.array(stats["heights"])
        print(f"\n  Image dimensions:")
        print(f"    Width  — min: {widths.min()}, max: {widths.max()}, "
              f"mean: {widths.mean():.0f}, median: {np.median(widths):.0f}")
        print(f"    Height — min: {heights.min()}, max: {heights.max()}, "
              f"mean: {heights.mean():.0f}, median: {np.median(heights):.0f}")

    # Corrupt images
    num_corrupt = len(stats["corrupt"])
    if num_corrupt > 0:
        print(f"\n  ⚠️  Corrupt images: {num_corrupt}")
        for path, err in stats["corrupt"][:10]:
            print(f"    - {path}")
            print(f"      Error: {err}")
        if num_corrupt > 10:
            print(f"    ... and {num_corrupt - 10} more")
    else:
        print(f"\n  ✅ No corrupt images found")

    # Small images
    num_small = len(stats["small"])
    if num_small > 0:
        print(f"\n  ⚠️  Small images (< {MIN_DIMENSION}×{MIN_DIMENSION}): {num_small}")
        for path, w, h in stats["small"][:5]:
            print(f"    - {path} ({w}×{h})")
        if num_small > 5:
            print(f"    ... and {num_small - 5} more")
    else:
        print(f"\n  ✅ No undersized images")

    # Duplicates
    duplicates = {h: paths for h, paths in stats["hashes"].items() if len(paths) > 1}
    if duplicates:
        total_dups = sum(len(p) - 1 for p in duplicates.values())
        print(f"\n  ⚠️  Duplicate images: {total_dups} duplicates across {len(duplicates)} groups")
        for i, (h, paths) in enumerate(list(duplicates.items())[:3]):
            print(f"    Group {i+1} (hash={h[:12]}...):")
            for p in paths[:3]:
                print(f"      - {p}")
            if len(paths) > 3:
                print(f"      ... and {len(paths) - 3} more")
        if len(duplicates) > 3:
            print(f"    ... and {len(duplicates) - 3} more groups")
    else:
        print(f"\n  ✅ No duplicate images (within this split)")


def check_cross_split_leakage(all_stats: dict):
    """Check for images that appear in multiple splits (data leakage)."""
    print(f"\n{'='*50}")
    print(f"  CROSS-SPLIT LEAKAGE CHECK")
    print(f"{'='*50}")

    split_hashes = {}
    for split_name, stats in all_stats.items():
        split_hashes[split_name] = set(stats["hashes"].keys())

    splits = list(split_hashes.keys())
    leakage_found = False

    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            s1, s2 = splits[i], splits[j]
            overlap = split_hashes[s1] & split_hashes[s2]
            if overlap:
                leakage_found = True
                print(f"\n  🚨 LEAKAGE: {len(overlap)} images shared between {s1} and {s2}!")
                for h in list(overlap)[:3]:
                    paths_1 = all_stats[s1]["hashes"][h]
                    paths_2 = all_stats[s2]["hashes"][h]
                    print(f"    Hash {h[:12]}...")
                    print(f"      {s1}: {paths_1[0]}")
                    print(f"      {s2}: {paths_2[0]}")
            else:
                print(f"\n  ✅ No leakage between {s1} and {s2}")

    if not leakage_found:
        print(f"\n  ✅ No cross-split data leakage detected!")


def main():
    parser = argparse.ArgumentParser(description="Validate dataset for ViT training")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "datasets" if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "training"
            else "datasets"
        ),
        help="Path to dataset root (contains train/validation/test)"
    )
    args = parser.parse_args()

    # Resolve path relative to project root if running from training/
    data_dir = args.data_dir
    if not os.path.isabs(data_dir):
        data_dir = os.path.abspath(data_dir)

    # Try common locations
    if not os.path.exists(data_dir):
        alt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")
        if os.path.exists(alt):
            data_dir = alt

    print(f"\n🔍 Validating dataset at: {data_dir}\n")

    if not os.path.exists(data_dir):
        print(f"❌ Dataset directory not found: {data_dir}")
        sys.exit(1)

    # Scan each split
    splits = {
        "train":      os.path.join(data_dir, "train"),
        "validation": os.path.join(data_dir, "validation"),
        "test":       os.path.join(data_dir, "test"),
    }

    all_stats = {}
    for split_name, split_path in splits.items():
        logger.info(f"Scanning {split_name}...")
        stats = scan_split(split_path, split_name)
        all_stats[split_name] = stats
        print_split_report(split_name, stats)

    # Cross-split leakage check
    check_cross_split_leakage(all_stats)

    # Summary
    print(f"\n{'='*50}")
    print(f"  SUMMARY")
    print(f"{'='*50}")
    grand_total = sum(s["total"] for s in all_stats.values())
    total_corrupt = sum(len(s["corrupt"]) for s in all_stats.values())
    total_small = sum(len(s["small"]) for s in all_stats.values())

    print(f"  Total images across all splits: {grand_total:,}")
    print(f"  Corrupt images: {total_corrupt}")
    print(f"  Undersized images: {total_small}")

    if total_corrupt == 0 and total_small == 0:
        print(f"\n  ✅ Dataset is clean and ready for training!")
    else:
        print(f"\n  ⚠️  Issues found — review the report above before training.")

    print()


if __name__ == "__main__":
    main()
