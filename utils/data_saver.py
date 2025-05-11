import csv
import os
from datetime import datetime

class DataSaver:
    """
    Класс для сохранения данных событий из Uniswap пула в CSV файл.
    Автоматически создает файл с датой в названии.
    """
    def __init__(self, filename_prefix="swap_data"):
        self.filename_prefix = filename_prefix
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.filename = f"{self.filename_prefix}_{self.current_date}.csv"
        self._initialize_file()
    
    def _initialize_file(self):
        """Инициализирует CSV файл с заголовками, если файл не существует"""
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'event', 'sender', 'recipient', 'amount0', 'amount1', 'sqrtPriceX96', 'liquidity', 'tick'])
            print(f"📄 Создан файл для сохранения данных: {self.filename}")
    
    def save_swap_data(self, data):
        """Сохраняет данные события Swap в CSV файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp, 
                data.get('event'), 
                data.get('sender'), 
                data.get('recipient'),
                data.get('amount0'),
                data.get('amount1'),
                data.get('sqrtPriceX96'),
                data.get('liquidity'),
                data.get('tick')
            ])
    
    def save_mint_data(self, data):
        """Сохраняет данные события Mint в CSV файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.filename.replace("swap", "mint"), 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp, 
                data.get('event'), 
                data.get('sender'),
                data.get('owner'),
                data.get('tickLower'),
                data.get('tickUpper'),
                data.get('amount'),
                data.get('amount0'),
                data.get('amount1')
            ])
    
    def save_burn_data(self, data):
        """Сохраняет данные события Burn в CSV файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.filename.replace("swap", "burn"), 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp, 
                data.get('event'),
                data.get('owner'),
                data.get('tickLower'),
                data.get('tickUpper'),
                data.get('amount'),
                data.get('amount0'),
                data.get('amount1')
            ]) 