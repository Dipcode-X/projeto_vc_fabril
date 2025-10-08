import argparse
import os
import random
import shutil
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def list_images(images_dir: Path):
    files = []
    for p in images_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            # Ignorar imagens que já estão em train/val
            parts = set(p.parts)
            if "train" in parts or "val" in parts:
                continue
            files.append(p)
    return files


essential_dirs = [
    ("images", "train"), ("images", "val"), ("labels", "train"), ("labels", "val")
]


def ensure_dirs(dataset_dir: Path):
    for a, b in essential_dirs:
        (dataset_dir / a / b).mkdir(parents=True, exist_ok=True)


def pair_label_for(image_path: Path, dataset_dir: Path, labels_dir_name: str = "labels") -> Path:
    # Supõe labels no formato YOLO com mesmo nome e extensão .txt
    rel = image_path.relative_to(dataset_dir / "images")
    # Remove possíveis subpastas em images
    label_rel = rel.with_suffix(".txt")
    return dataset_dir / labels_dir_name / label_rel


def split_dataset(dataset_dir: str, val_ratio: float = 0.2, seed: int = 42, move: bool = False):
    dataset_dir = Path(dataset_dir)
    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    if not images_dir.exists():
        raise SystemExit(f"Pasta de imagens não encontrada: {images_dir}")
    if not labels_dir.exists():
        print(f"[AVISO] Pasta de labels não encontrada: {labels_dir} (imagens poderão ir sem label)")

    ensure_dirs(dataset_dir)

    imgs = list_images(images_dir)
    if not imgs:
        raise SystemExit(f"Nenhuma imagem encontrada em {images_dir}")

    random.Random(seed).shuffle(imgs)
    n_val = max(1, int(len(imgs) * val_ratio))
    val_set = set(imgs[:n_val])

    op = shutil.move if move else shutil.copy2

    moved_train = moved_val = 0

    for img in imgs:
        subset = "val" if img in val_set else "train"
        dst_img = dataset_dir / "images" / subset / img.name
        dst_img.parent.mkdir(parents=True, exist_ok=True)
        op(str(img), str(dst_img))

        # Label com caminhos relativos, mantendo hierarquia se houver
        lbl_src = pair_label_for(img, dataset_dir)
        if lbl_src.exists():
            dst_lbl = dataset_dir / "labels" / subset / lbl_src.name
            dst_lbl.parent.mkdir(parents=True, exist_ok=True)
            op(str(lbl_src), str(dst_lbl))
        else:
            # Sem label correspondente é permitido, apenas loga
            pass

        if subset == "val":
            moved_val += 1
        else:
            moved_train += 1

    print(f"Concluído. Treino: {moved_train} imagens, Validação: {moved_val} imagens.")
    print(f"Estrutura final:")
    print(f"  {dataset_dir / 'images' / 'train'}")
    print(f"  {dataset_dir / 'images' / 'val'}")
    print(f"  {dataset_dir / 'labels' / 'train'}")
    print(f"  {dataset_dir / 'labels' / 'val'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Divide dataset YOLO em train/val movendo ou copiando imagens e labels.")
    parser.add_argument("dataset", help="Caminho da pasta do dataset (contendo 'images' e 'labels')")
    parser.add_argument("--val", type=float, default=0.2, help="Proporção de validação (default: 0.2)")
    parser.add_argument("--seed", type=int, default=42, help="Seed para embaralhamento (default: 42)")
    parser.add_argument("--move", action="store_true", help="Mover ao invés de copiar (default: copiar)")

    args = parser.parse_args()
    split_dataset(args.dataset, val_ratio=args.val, seed=args.seed, move=args.move)
