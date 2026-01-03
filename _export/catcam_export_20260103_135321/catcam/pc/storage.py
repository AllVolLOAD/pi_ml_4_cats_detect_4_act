"""
Утилиты для работы с путями хранения (поддержка USB дисков, сетевых путей)
"""

import os
from pathlib import Path
from typing import Optional


class StoragePaths:
    """Управление путями к данным, моделям, логам"""
    
    def __init__(self, config: dict):
        """
        Инициализация путей из конфигурации
        
        Args:
            config: словарь с секцией 'storage' из config.yaml
        """
        storage_config = config.get('storage', {})
        
        # Базовый путь
        base_path = storage_config.get('base_path', 'data')
        if os.path.isabs(base_path):
            self.base_path = Path(base_path)
        else:
            # Относительно текущей директории (catcam/pc/)
            self.base_path = Path(__file__).parent.parent / base_path
        
        # Подпапки
        self.models_dir = Path(self.base_path) / storage_config.get('models_dir', 'models')
        self.datasets_dir = Path(self.base_path) / storage_config.get('datasets_dir', 'datasets')
        self.logs_dir = Path(self.base_path) / storage_config.get('logs_dir', 'logs')
        self.checkpoints_dir = Path(self.base_path) / storage_config.get('checkpoints_dir', 'checkpoints')
        
        # Создаем директории если их нет
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
    
    def get_model_path(self, model_path: str) -> Path:
        """
        Получить полный путь к модели
        
        Args:
            model_path: путь из config (может быть относительным, абсолютным или просто именем файла)
        
        Returns:
            Path объект с полным путем к модели
        """
        if os.path.isabs(model_path):
            return Path(model_path)
        
        # Если это просто имя файла (yolov8n.pt), ищем в текущей директории
        if '/' not in model_path and '\\' not in model_path:
            local_path = Path(__file__).parent / model_path
            if local_path.exists():
                return local_path
            # Если не найден локально, возвращаем путь в models_dir
            return self.models_dir / model_path
        
        # Относительный путь - ищем в models_dir
        return self.models_dir / model_path
    
    def get_checkpoint_path(self, experiment_name: str = "cat_activity") -> Path:
        """
        Получить путь к директории чекпоинтов для эксперимента
        
        Args:
            experiment_name: имя эксперимента
        
        Returns:
            Path к директории чекпоинтов
        """
        checkpoint_path = self.checkpoints_dir / experiment_name
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        return checkpoint_path
    
    def get_dataset_path(self, dataset_name: str) -> Path:
        """
        Получить путь к датасету
        
        Args:
            dataset_name: имя датасета или подпуть
        
        Returns:
            Path к датасету
        """
        return self.datasets_dir / dataset_name
    
    def __repr__(self):
        return f"StoragePaths(base={self.base_path}, models={self.models_dir}, datasets={self.datasets_dir}, logs={self.logs_dir}, checkpoints={self.checkpoints_dir})"

