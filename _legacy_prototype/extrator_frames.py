import cv2
import os

# --- Configurações ---
VIDEO_SOURCE = r"c:\Users\ti-005\Desktop\projeto_vc_fabril\videos_test\WIN_20250721_09_03_05_Pro.mp4"
OUTPUT_DIR = "dataset/images"
FRAME_INTERVAL = 20 
# ---------------------

def extrair_frames():
    """
    Extrai frames de um vídeo e os salva em um diretório de saída.
    """
    # Cria o diretório de saída se não existir
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"Erro: Não foi possível abrir o vídeo em '{VIDEO_SOURCE}'")
        return

    frame_count = 0
    saved_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Fim do vídeo.")
            break

        # Salva o frame no intervalo especificado
        if frame_count % FRAME_INTERVAL == 0:
            output_path = os.path.join(OUTPUT_DIR, f"frame_{saved_count:04d}.jpg")
            cv2.imwrite(output_path, frame)
            print(f"Salvo: {output_path}")
            saved_count += 1
        
        frame_count += 1

    cap.release()
    print(f"\nExtração concluída. Total de {saved_count} frames salvos em '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    extrair_frames()