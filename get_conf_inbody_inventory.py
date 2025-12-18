import requests
import re
import json
import argparse
import getpass
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

def get_password_interactive(prompt: str = "Введите пароль: ") -> str:
    """Получить пароль интерактивно (без отображения ввода)"""
    return getpass.getpass(prompt)

def main():
    parser = argparse.ArgumentParser(
        description='Извлечение IP-адресов из таблицы Confluence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  python script.py --url https://confluence.example.com --username user --page-id 123456
  python script.py --url https://confluence.example.com --username user --password pass123 --page-id 123456
  python script.py --url https://confluence.example.com --username user --page-id 123456 --output my_ips.txt
        '''
    )
    
    # Обязательные аргументы
    parser.add_argument('--url', required=True, help='URL Confluence (например, https://confluence.example.com)')
    parser.add_argument('--username', required=True, help='Имя пользователя Confluence')
    parser.add_argument('--page-id', required=True, help='ID страницы Confluence')
    
    # Необязательные аргументы
    parser.add_argument('--password', help='Пароль (если не указан, запросится интерактивно)')
    parser.add_argument('--output', default='ip_addresses.txt', help='Имя выходного файла (по умолчанию: ip_addresses.txt)')
    parser.add_argument('--no-ssl-verify', action='store_true', help='Отключить проверку SSL сертификата')
    
    args = parser.parse_args()
    
    # Получаем пароль
    if args.password:
        password = args.password
    else:
        password = get_password_interactive(f"Введите пароль для пользователя {args.username}: ")
    
    # Создаем клиент Confluence
    confluence = ConfluenceClient(args.url, args.username, password)
    
    # Опционально отключаем проверку SSL
    if args.no_ssl_verify:
        confluence.session.verify = False
        requests.packages.urllib3.disable_warnings()
    
    try:
        # 1. Получаем содержимое страницы
        print(f"Получаем содержимое страницы {args.page_id}...")
        page_content = confluence.get_page_content(args.page_id)
        
        # 2. Извлекаем таблицу
        print("Извлекаем таблицу...")
        table_html = confluence.extract_table_from_content(page_content)
        
        # 3. Извлекаем IP-адреса
        print("Извлекаем IP-адреса...")
        ip_addresses = confluence.extract_ip_addresses(table_html)
        
        # 4. Сохраняем в файл
        confluence.save_ips_to_file(ip_addresses, args.output)
        
        # Выводим найденные адреса
        if ip_addresses:
            print(f"\nНайдено {len(ip_addresses)} уникальных IP-адресов:")
            for ip in ip_addresses:
                print(f"  - {ip}")
        else:
            print("IP-адреса не найдены в таблице")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
