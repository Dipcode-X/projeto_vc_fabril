"""
Teste EVOLUTIVO da Câmera - Agora com StateManagerAdvanced integrado
Evolução incremental: Câmera + YOLO + StateManager industrial
"""

import cv2
from queue import Empty

from central_manager.core_advanced.orchestrator import Orchestrator

def main():
    """Função principal que inicializa e executa o orquestrador de câmeras."""
    print("\n" + "=" * 60)
    print(" Iniciando SIAC - Sistema Integrado de Análise de Caixas")
    print("=" * 60)

    orchestrator = Orchestrator()
    camera_source = 0  # Pode ser o índice da câmera ou o caminho para um arquivo de vídeo
    orchestrator.add_camera(camera_source)
    orchestrator.start()

    try:
        # Loop principal para visualização e controle
        while True:
            camera_data = orchestrator.get_camera_data(camera_source)
            if not camera_data:
                print(f"Erro: Não foi possível obter dados para a câmera {camera_source}")
                break

            try:
                # Tenta pegar o último frame da fila sem bloquear
                data = camera_data['queue'].get_nowait()
                frame = data['frame']
                cv2.imshow(f'SIAC - Câmera {camera_source}', frame)

            except Empty:
                # Fila vazia, o que é normal. Continue para o próximo ciclo.
                pass
            
            # Controle por teclado
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC para sair
                break
            
            # Acessa o processador para enviar comandos
            processor = camera_data['processor']
            if key == ord(' '):
                processor.paused = not processor.paused
            elif key == ord('d'):
                processor.detection_enabled = not processor.detection_enabled
            elif key == ord('r'):
                processor.state_manager._resetar_sistema()
                print(f"\n🔄 StateManager da câmera {camera_source} resetado pelo usuário.")

    except KeyboardInterrupt:
        print("\nInterrupção pelo usuário detectada.")
    
    finally:
        print("\nFinalizando a aplicação...")
        orchestrator.stop()
        cv2.destroyAllWindows()
        print("=" * 60)
        print(" Aplicação finalizada com sucesso.")

if __name__ == "__main__":
    main()
