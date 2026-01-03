"""
Обучение модели YOLOv8 для детекции активности кошек
"""

from ultralytics import YOLO
from pathlib import Path
import yaml
import argparse
from storage import StoragePaths


def train(
    model_size: str = "n",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    data_yaml: str = None,
    config_path: str = "config.yaml",
    resume: bool = False,
    checkpoint: str = None
):
    """
    Обучение YOLOv8 модели
    
    Args:
        model_size: размер модели (n, s, m, l, x)
        epochs: количество эпох
        imgsz: размер изображения
        batch: размер батча
        data_yaml: путь к data.yaml датасета
        config_path: путь к config.yaml
        resume: продолжить обучение с последнего чекпоинта
        checkpoint: путь к конкретному чекпоинту для resume
    """
    # Загружаем конфигурацию
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    storage = StoragePaths(config)
    
    # Путь к датасету
    if data_yaml is None:
        # По умолчанию ищем в storage/datasets
        data_yaml = str(storage.get_dataset_path("dataset/data.yaml"))
        if not Path(data_yaml).exists():
            # Fallback на старый путь
            data_yaml = "../data/dataset/data.yaml"
    
    # Определяем путь к начальной модели или чекпоинту
    if resume:
        if checkpoint:
            model_path = checkpoint
        else:
            # Ищем последний чекпоинт
            checkpoint_dir = storage.get_checkpoint_path("cat_activity")
            last_checkpoint = checkpoint_dir / "weights" / "last.pt"
            if last_checkpoint.exists():
                model_path = str(last_checkpoint)
                print(f"[Train] Продолжение обучения с: {model_path}")
            else:
                print("[Train] Чекпоинт не найден, начинаем с нуля")
                model_path = f"yolov8{model_size}.pt"
    else:
        model_path = f"yolov8{model_size}.pt"
    
    print(f"[Train] Загрузка модели: {model_path}")
    model = YOLO(model_path)
    
    # Путь для сохранения результатов
    checkpoint_dir = storage.get_checkpoint_path("cat_activity")
    
    print(f"[Train] Начало обучения:")
    print(f"  Storage: {storage.base_path}")
    print(f"  Checkpoints: {checkpoint_dir}")
    print(f"  Epochs: {epochs}")
    print(f"  Image size: {imgsz}")
    print(f"  Batch: {batch}")
    print(f"  Data: {data_yaml}")
    print(f"  Resume: {resume}")
    
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=0,  # GPU
        project=str(checkpoint_dir.parent),
        name=checkpoint_dir.name,
        exist_ok=True,
        patience=50,
        save=True,
        plots=True,
        resume=resume
    )
    
    best_model_path = Path(results.save_dir) / "weights" / "best.pt"
    
    print("\n" + "="*50)
    print("Обучение завершено!")
    print(f"Лучшая модель: {best_model_path}")
    print(f"Последний чекпоинт: {Path(results.save_dir) / 'weights' / 'last.pt'}")
    print("="*50)
    
    # Валидация
    print("\nВалидация...")
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    
    # Копируем лучшую модель в models_dir для использования
    import shutil
    final_model_path = storage.models_dir / "best.pt"
    shutil.copy2(best_model_path, final_model_path)
    print(f"\nМодель скопирована в: {final_model_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обучение YOLOv8 модели для детекции котов")
    parser.add_argument("--model", type=str, default="n", choices=["n", "s", "m", "l", "x"], help="Размер модели")
    parser.add_argument("--epochs", type=int, default=100, help="Количество эпох")
    parser.add_argument("--imgsz", type=int, default=640, help="Размер изображения")
    parser.add_argument("--batch", type=int, default=16, help="Размер батча")
    parser.add_argument("--data", type=str, default=None, help="Путь к data.yaml датасета")
    parser.add_argument("--config", type=str, default="config.yaml", help="Путь к config.yaml")
    parser.add_argument("--resume", action="store_true", help="Продолжить обучение с последнего чекпоинта")
    parser.add_argument("--checkpoint", type=str, default=None, help="Путь к конкретному чекпоинту для resume")
    args = parser.parse_args()
    
    train(
        model_size=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        data_yaml=args.data,
        config_path=args.config,
        resume=args.resume,
        checkpoint=args.checkpoint
    )

