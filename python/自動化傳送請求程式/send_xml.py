import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 設定區域 ---
XML_URL = "https://postest2.einvoice.com.tw/GetInvoiceXML.ashx"
JSON_URL = "https://postest2.einvoice.com.tw/GetInvoice.ashx"

# 2. 存放資料的檔案路徑
file_path = r"D:\D\wilsonhuang\Worktime\python\自動化傳送請求程式\data\Send_Request.txt" 

# 3. 選擇傳送格式: 'XML' 或 'JSON'
DATA_FORMAT = 'JSON'  # 可改為 'JSON'

# 4. 加速設定
USE_MULTITHREADING = True  # True: 使用多線程加速, False: 逐筆發送
MAX_WORKERS = 5  # 同時發送的線程數量 (建議 3-10)
DELAY_BETWEEN_REQUESTS = 0  # 每筆請求間隔秒數 (0 表示無延遲，建議 0-0.2)

# 5. HTTP Header 設定 (模擬 Postman 的 Headers)
headers = {
    'Authorization': 'Bearer YOUR_TOKEN_HERE', # 如果有 Token 驗證請填這，沒用到的話可刪除
}

def send_single_request(index, data_content, format_name, target_url):
    """發送單筆請求"""
    try:
        # 根據格式處理資料
        if DATA_FORMAT.upper() == 'JSON':
            try:
                # 驗證是否為有效的 JSON
                json.loads(data_content)
                data_to_send = data_content.encode('utf-8')
            except json.JSONDecodeError:
                return f"[警告] 第 {index+1} 筆 - JSON 格式錯誤，跳過此筆"
        else:
            # XML 格式直接傳送
            data_to_send = data_content.encode('utf-8')

        # 發送 POST 請求
        response = requests.post(target_url, data=data_to_send, headers=headers, timeout=30)

        # 檢查結果
        if response.status_code == 200:
            return f"[成功] 第 {index+1} 筆\n伺服器完整回應: {response.text}"
        else:
            return f"[失敗] 第 {index+1} 筆 - 狀態碼: {response.status_code}, 錯誤訊息: {response.text}"
    
    except requests.exceptions.Timeout:
        return f"[失敗] 第 {index+1} 筆 - 請求超時"
    except Exception as e:
        return f"[錯誤] 第 {index+1} 筆 - {str(e)}"

def send_requests():
    # 根據選擇的格式設定 Content-Type 和 URL
    if DATA_FORMAT.upper() == 'JSON':
        headers['Content-Type'] = 'application/json'
        format_name = 'JSON'
        target_url = JSON_URL
    else:
        headers['Content-Type'] = 'application/xml'
        format_name = 'XML'
        target_url = XML_URL
    
    print(f"使用格式: {format_name}")
    print(f"目標 URL: {target_url}")
    print(f"多線程模式: {'啟用' if USE_MULTITHREADING else '停用'}")
    if USE_MULTITHREADING:
        print(f"並行線程數: {MAX_WORKERS}")
    
    try:
        # 開啟檔案讀取每一行
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # 過濾空白行
        data_list = [(index, line.strip()) for index, line in enumerate(lines) if line.strip()]
        
        print(f"開始處理，共計 {len(data_list)} 筆資料...")
        start_time = time.time()

        if USE_MULTITHREADING:
            # 使用多線程模式
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # 提交所有任務
                futures = {
                    executor.submit(send_single_request, index, content, format_name, target_url): index 
                    for index, content in data_list
                }
                
                # 處理完成的結果
                for future in as_completed(futures):
                    result = future.result()
                    print(result)
                    if DELAY_BETWEEN_REQUESTS > 0:
                        time.sleep(DELAY_BETWEEN_REQUESTS)
        else:
            # 逐筆發送模式
            for index, content in data_list:
                result = send_single_request(index, content, format_name, target_url)
                print(result)
                if DELAY_BETWEEN_REQUESTS > 0:
                    time.sleep(DELAY_BETWEEN_REQUESTS)
        
        elapsed_time = time.time() - start_time
        print(f"\n全部完成！總耗時: {elapsed_time:.2f} 秒")

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {file_path}")
    except Exception as e:
        print(f"發生非預期錯誤：{e}")

if __name__ == "__main__":
    send_requests()