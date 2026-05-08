import os
from datetime import datetime

# --- 設定區域 ---
# 1. 檔案名稱列表的 TXT 檔案路徑
INPUT_FILE = r"D:\D\wilsonhuang\Worktime\python\自動化語法產生程式\data\filenames.txt"

# 2. 輸出的 SQL 檔案路徑（可選，如果不想輸出到檔案，設為 None）
OUTPUT_FILE = r"D:\D\wilsonhuang\Worktime\python\自動化語法產生程式\output\generated_sql.sql"

# 3. SQL 語法模板設定
SQL_TEMPLATE = {
    'status': '2',
    'count': '0',
    'send_status': '0',
    'ip_port': '',
    'error_code': '00000'
}

def get_current_timestamp():
    """取得當前時間戳記，格式：YYYYMMDDHHmmss"""
    return datetime.now().strftime('%Y%m%d%H%M%S')

def generate_sql(file_name, timestamp):
    """生成單筆 SQL UPDATE 語句"""
    sql = (
        f"UPDATE XML_MESSAGE SET "
        f"status='{SQL_TEMPLATE['status']}', "
        f"count='{SQL_TEMPLATE['count']}', "
        f"send_status='{SQL_TEMPLATE['send_status']}', "
        f"ip_port='{SQL_TEMPLATE['ip_port']}', "
        f"error_code='{SQL_TEMPLATE['error_code']}', "
        f"UPDATE_DTM='{timestamp}' "
        f"WHERE file_name='{file_name}'"
    )
    return sql

def read_filenames(file_path):
    """從 TXT 檔案讀取檔案名稱列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 讀取每一行並去除空白行
            filenames = [line.strip() for line in f.readlines() if line.strip()]
        return filenames
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {file_path}")
        return []
    except Exception as e:
        print(f"讀取檔案時發生錯誤：{e}")
        return []

def save_sql_to_file(sql_statements, output_path):
    """將 SQL 語句儲存到檔案"""
    try:
        # 確保輸出目錄存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for sql in sql_statements:
                f.write(sql + ';\n')
        
        print(f"\n✓ SQL 語法已儲存到：{output_path}")
        return True
    except Exception as e:
        print(f"儲存檔案時發生錯誤：{e}")
        return False

def main():
    print("="*80)
    print("SQL UPDATE 語法生成工具")
    print("="*80)
    
    # 讀取檔案名稱列表
    print(f"\n讀取檔案名稱列表：{INPUT_FILE}")
    filenames = read_filenames(INPUT_FILE)
    
    if not filenames:
        print("沒有找到檔案名稱，程式結束。")
        return
    
    print(f"共讀取 {len(filenames)} 個檔案名稱\n")
    
    # 取得當前時間戳記
    timestamp = get_current_timestamp()
    print(f"使用時間戳記：{timestamp}\n")
    
    # 生成 SQL 語句
    sql_statements = []
    print("生成的 SQL 語句：")
    print("-"*80)
    
    for idx, filename in enumerate(filenames, 1):
        sql = generate_sql(filename, timestamp)
        sql_statements.append(sql)
        print(f"{idx}. {sql};")
    
    print("-"*80)
    print(f"\n共生成 {len(sql_statements)} 條 SQL 語句")
    
    # 儲存到檔案（如果有設定輸出路徑）
    if OUTPUT_FILE:
        save_sql_to_file(sql_statements, OUTPUT_FILE)
    
    # 詢問是否複製到剪貼簿
    try:
        choice = input("\n是否要複製所有 SQL 到剪貼簿？(y/n): ").strip().lower()
        if choice == 'y':
            try:
                import pyperclip
                all_sql = '\n'.join([sql + ';' for sql in sql_statements])
                pyperclip.copy(all_sql)
                print("✓ 已複製到剪貼簿！")
            except ImportError:
                print("提示：安裝 pyperclip 模組可啟用剪貼簿功能 (pip install pyperclip)")
    except:
        pass
    
    print("\n程式執行完成！")
    print("="*80)

if __name__ == "__main__":
    main()
