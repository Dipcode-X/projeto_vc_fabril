import os
import shutil
import random
import argparse

def organizar_arquivos(dataset_path, train_ratio=0.8):
    """
    Organiza um dataset de imagens e rótulos YOLO em pastas de treino e validação.

    A estrutura de pastas esperada é:
    - dataset_path/
        - images/ (contém todas as imagens .jpg, .png, etc.)
        - labels/ (contém todos os rótulos .txt)

    O script irá criar as seguintes subpastas e distribuir os arquivos:
    - dataset_path/
        - images/
            - train/
            - val/
        - labels/
            - train/
            - val/
    """
    print(f"--- Iniciando organização do dataset em: {dataset_path} ---")

    images_dir = os.path.join(dataset_path, 'images')
    labels_dir = os.path.join(dataset_path, 'labels')

    # Verifica se os diretórios de origem existem
    if not os.path.isdir(images_dir) or not os.path.isdir(labels_dir):
        print(f"[ERRO] Diretórios 'images' e/ou 'labels' não encontrados em '{dataset_path}'.")
        print("Por favor, coloque todas as suas imagens em 'images/' e todos os rótulos em 'labels/'.")
        return

    # Cria os diretórios de destino
    train_img_dir = os.path.join(images_dir, 'train')
    val_img_dir = os.path.join(images_dir, 'val')
    train_lbl_dir = os.path.join(labels_dir, 'train')
    val_lbl_dir = os.path.join(labels_dir, 'val')

    # Loop para criar os diretórios de destino
    for path in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        os.makedirs(path, exist_ok=True)
        # Limpa diretórios antigos para garantir uma nova divisão limpa
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))

    # Pega todos os nomes de arquivo de imagem (sem extensão)
    image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    if not image_files:
        print("[AVISO] Nenhuma imagem encontrada no diretório 'images'. Saindo.")
        return

    random.shuffle(image_files)

    # Calcula o ponto de divisão
    split_point = int(len(image_files) * train_ratio)
    train_files = image_files[:split_point]
    val_files = image_files[split_point:]

    # Função auxiliar para mover os arquivos
    def mover_arquivos(file_list, dest_img_dir, dest_lbl_dir):
        moved_count = 0
        for filename in file_list:
            base_name, _ = os.path.splitext(filename)
            label_filename = f"{base_name}.txt"

            src_img_path = os.path.join(images_dir, filename)
            src_lbl_path = os.path.join(labels_dir, label_filename)

            # Move apenas se ambos, imagem e rótulo, existirem
            if os.path.exists(src_img_path) and os.path.exists(src_lbl_path):
                shutil.move(src_img_path, os.path.join(dest_img_dir, filename))
                shutil.move(src_lbl_path, os.path.join(dest_lbl_dir, label_filename))
                moved_count += 1
            else:
                print(f"[AVISO] Imagem '{filename}' ou rótulo '{label_filename}' não encontrado. Pulando.")
        return moved_count

    print("Movendo arquivos de treino...")
    num_train = mover_arquivos(train_files, train_img_dir, train_lbl_dir)

    print("Movendo arquivos de validação...")
    num_val = mover_arquivos(val_files, val_img_dir, val_lbl_dir)

    print("\n--- Organização Concluída ---")
    print(f"Total de imagens de treino: {num_train}")
    print(f"Total de imagens de validação: {num_val}")
    print("Dataset pronto para o treinamento.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Organiza um dataset YOLO em pastas de treino e validação.")
    parser.add_argument('--path', type=str, required=True, help='Caminho para o diretório raiz do dataset (ex: dataset/1_item_counter).')
    args = parser.parse_args()

    organizar_arquivos(args.path)
