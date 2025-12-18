import requests
import re
import json
from typing import List

class ConfluenceClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def get_page_content(self, page_id: str) -> dict:
        """Получить содержимое страницы по ID"""
        url = f"{self.base_url}/rest/api/content/{page_id}?expand=body.storage"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении страницы: {e}")
            raise
    
    def extract_table_from_content(self, content: dict) -> str:
        """Извлечь HTML таблицы из содержимого страницы"""
        try:
            storage_content = content['body']['storage']['value']
            # Ищем таблицу в формате Confluence
            table_match = re.search(r'<table[^>]*>(.*?)</table>', storage_content, re.DOTALL)
            if table_match:
                return table_match.group(0)
            else:
                raise ValueError("Таблица не найдена на странице")
        except KeyError as e:
            print(f"Ошибка при извлечении таблицы: {e}")
            raise
    
    def extract_ip_addresses(self, table_html: str) -> List[str]:
        """Извлечь IP-адреса из HTML таблицы"""
        # Регулярное выражение для поиска IPv4 адресов
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        
        # Удаляем HTML теги для чистого текста
        clean_text = re.sub(r'<[^>]+>', ' ', table_html)
        
        # Ищем все IP-адреса
        ip_addresses = re.findall(ip_pattern, clean_text)
        
        # Фильтруем валидные IP-адреса
        valid_ips = []
        for ip in ip_addresses:
            if self.is_valid_ip(ip):
                valid_ips.append(ip)
        
        return list(set(valid_ips))  # Убираем дубликаты
    
    def is_valid_ip(self, ip: str) -> bool:
        """Проверить валидность IP-адреса"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            except ValueError:
                return False
        
        return True
    
    def save_ips_to_file(self, ip_addresses: List[str], filename: str = 'ip_addresses.txt'):
        """Сохранить IP-адреса в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('[labrat]\n')
                for ip in ip_addresses:
                    f.write(ip + '\n')
            print(f"Найдено {len(ip_addresses)} уникальных IP-адресов. Сохранено в файл: {filename}")
        except IOError as e:
            print(f"Ошибка при записи в файл: {e}")
            raise

def main():
    # Конфигурация
    CONFLUENCE_URL = ""
    USERNAME = ""
    PASSWORD = ""  # Рекомендуется использовать API токен вместо пароля
    PAGE_ID = ""  # ID страницы с таблицей
    
    # Создаем клиент Confluence
    confluence = ConfluenceClient(CONFLUENCE_URL, USERNAME, PASSWORD)
    
    try:
        # 1. Получаем содержимое страницы
        print("Получаем содержимое страницы...")
        page_content = confluence.get_page_content(PAGE_ID)
        
        # 2. Извлекаем таблицу
        print("Извлекаем таблицу...")
        table_html = confluence.extract_table_from_content(page_content)
        
        # 3. Извлекаем IP-адреса
        print("Извлекаем IP-адреса...")
        ip_addresses = confluence.extract_ip_addresses(table_html)
        
        # 4. Сохраняем в файл
        confluence.save_ips_to_file(ip_addresses)
        
        # Выводим найденные адреса
        if ip_addresses:
            print("\nНайденные IP-адреса:")
            for ip in ip_addresses:
                print(f"  - {ip}")
        else:
            print("IP-адреса не найдены в таблице")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":

    main()

