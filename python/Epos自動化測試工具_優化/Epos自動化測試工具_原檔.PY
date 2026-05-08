from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from openpyxl import workbook
from openpyxl.styles import NamedStyle
from PIL import Image
from datetime import datetime
import pytesseract
import time
import os
import glob
import pyautogui
import pandas as pd
import warnings
import openpyxl
import captcha_solver
import traceback

# ✅ 等待並點擊元素

def wait_and_click(driver, by, value, timeout=3):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return True
    except Exception as e:
        print(f"❌ 點擊元素失敗 ({value}): {e}")
        return False

# ✅ 等待並輸入文字

def wait_and_input(driver, by, value, input_text, timeout=3):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        element.clear()
        element.send_keys(input_text)
        return True
    except Exception as e:
        print(f"❌ 輸入元素失敗 ({value}): {e}")
        return False

# ✅ 儲存 Excel（加強錯誤處理）

def write_excel_safely(df, output_file_path):
    try:
        df.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"📄 已儲存至 {output_file_path}")
    except Exception as e:
        print(f"❌ Excel 寫入失敗：{e}")

# ✅ 接受所有 alert 視窗


def accept_all_alerts(driver, max_alerts=3):
    for _ in range(max_alerts):
        try:
            WebDriverWait(driver, 2).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
        except:
            break
def get_invoice_data(path):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        if df.empty:
            print(f"{path} 沒有發票資料，結束處理")
        return df
    except Exception as e:
        print(f"讀取 Excel 發生錯誤: {e}")
        return pd.DataFrame() 
def check_invoice_count(company_id, invoice_number,invoice_data, error_file_path):
    # """  檢查發票在「電子發票傳送查詢」中是否有兩筆以上記錄 """
        try:
            deleted_any = False
            invoice_number_str = str(invoice_number).strip()
            menu_element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "營業人查詢作業")]'))
            )
            menu_element.click()
            time.sleep(1)


            query_element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@href="/AS0102"]'))
            )
            query_element.click()
            time.sleep(1)


            search_company_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "btnSrachCom"))
            )
            search_company_btn.click()
            time.sleep(1)


            company_input = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "company_IdQuery"))
            )
            company_input.clear()
            company_input.send_keys(company_id)
            print(f'輸入統編:{company_id}成功')
            time.sleep(1)


            search_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "EAqueryQ"))
            )
            search_btn.click()
            time.sleep(3)

            # 點選查詢結果的統編 (假設它是第一筆)
            company_result = WebDriverWait(driver, 2).until(
                 EC.element_to_be_clickable((By.XPATH, '//tbody[@id="tbCompanyId"]//tr[1]/td[1]/span'))
             )
            driver.execute_script("arguments[0].click();", company_result)  
            time.sleep(2)

            # 輸入發票號碼
            invoice_input = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.ID, "invoiceNumberQuery"))  
            )
            invoice_input.clear()
            invoice_input.send_keys(invoice_number)
            print(f'輸入發票號碼:{invoice_number}成功')
            time.sleep(1)

            # 按下查詢按鈕
            invoice_search_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "queryButton"))  # 這個 ID 需確認
            )
            invoice_search_btn.click()
            time.sleep(3)
            results_table = driver.find_elements(By.XPATH, '//tbody[@id="tbId"]/tr')
            record_count = len(results_table)
            print(f"發票號碼 {invoice_number} 查詢結果，共 {record_count} 筆")

            invoice_Status_count = {}
            error_invoice = []

            for idx,row in enumerate(results_table, start=1):
                columns = row.find_elements(By.TAG_NAME, "td")
                invoice_status = columns[6].text.strip()  # 第 7 欄為「發票狀態」
                error_reason = columns[9].text.strip()   # 第 10 欄為「處理結果」
                invoice_Status_count[invoice_status] = invoice_Status_count.get(invoice_status, 0) + 1
                error_invoice.append((idx, invoice_status, error_reason))
            invoice_number_str = str(invoice_number).strip()
            

        # --- 判斷邏輯 ---
        # 1️⃣ 只有一列
            if record_count == 1:
              idx, status, reason = error_invoice[0]
              if reason == "大平台回覆成功":
                  print(f"發票 {invoice_number_str} 單筆成功，刪除 Excel 及系統資料")
                  before_count = len(invoice_data)
                  invoice_data = invoice_data[~invoice_data["發票/折讓單號碼"].astype(str).str.strip().eq(invoice_number_str)]
                  after_count = len(invoice_data)
                  if before_count != after_count:
                       print(f"→ Excel 更新: 原本 {before_count} 筆，現在剩 {after_count} 筆待處理")
                       invoice_data.to_excel(error_file_path, index=False, engine='openpyxl')
                  deleted_any = True
                  return "auto_deleted"
              else:
                 print(f"發票 {invoice_number_str} 單筆失敗，人工確認")
                 return "manual_check"

            elif record_count >= 2:
                 fail_rows = [(idx, status, reason) for idx, status, reason in error_invoice
                            if reason in ["大平台回覆失敗", "小平台解析失敗"]]
  
                 if fail_rows:
                        print(f"發票 {invoice_number_str} 發現 {len(fail_rows)} 筆失敗列，開始刪除...")
                        for idx, status, reason in fail_rows:
                          print(f"  → 刪除失敗列: 第 {idx} 列 - 狀態: {status}, 處理結果: {reason}")
                          delete_invoice(company_id, invoice_number_str)

                        before_count = len(invoice_data)
                        invoice_data = invoice_data[~invoice_data["發票/折讓單號碼"].astype(str).str.strip().eq(invoice_number_str)]
                        after_count = len(invoice_data)
                        if before_count != after_count:
                            print(f"已刪除 Excel 中發票 {invoice_number_str}")
                            print(f"→ Excel 更新: 原本 {before_count} 筆，現在剩 {after_count} 筆待處理")
                            invoice_data.to_excel(error_file_path, index=False, engine='openpyxl')
                        deleted_any = True
                        return "auto_deleted"
                 else:
                     print(f"發票 {invoice_number_str} 沒有失敗列，需人工確認")
                     return "manual_check"

            return deleted_any

        except Exception as e:
          print(f'檢查發票記錄失敗:{e}')
          return False
        
def delete_invoice(company_id,invoice_number):
        #   刪除發票
          try:
              element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(text(), "客服維運作業")]'))
              )
              driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", element)  # 修改元素顯示屬性
              driver.execute_script("arguments[0].click();", element)  # 點擊元素  
              element = WebDriverWait(driver, 2).until(
              EC.element_to_be_clickable((By.XPATH, '//a[text()="發票異常處理"]'))
              )
              element.click()  # 點擊按鈕
              company_input = WebDriverWait(driver, 2).until(
              EC.presence_of_element_located((By.XPATH, '//input[@name="uniformNoQuery"]'))
              )
              company_input.clear()
              company_input.send_keys(company_id)

              invoice_input = WebDriverWait(driver, 2).until(
              EC.presence_of_element_located((By.XPATH, '//input[@name="invoiceNumberQuery"]'))
              )

              invoice_input.clear()  # 清空輸入框
              invoice_input.send_keys(invoice_number)
              search_button = WebDriverWait(driver, 5).until(
              EC.element_to_be_clickable((By.XPATH, '//input[@id="queryButton"]'))
              )
              search_button.click()
              print(f"查詢發票 {invoice_number}...中")

              results_table1 = WebDriverWait(driver, 2).until(
              EC.presence_of_all_elements_located((By.XPATH, '//tbody[@id="tbId"]/tr'))
              )
              record_count1 = len(results_table1)
              print(f"發票號碼: {invoice_number} 查詢結果，共 {record_count1} 筆")
              print(f'準備刪除發票:{invoice_number}')
            #   user_input = input("請輸入'確認'來刪除該張發票或輸入'不確認'跳過這筆發票:'")
              time.sleep(2)
              checkbox = WebDriverWait(driver, 2).until(
              EC.presence_of_element_located((By.XPATH, f'//input[@type="checkbox" and @name ="selList"]'))
              )
              checkbox.click()
              delete_error_invoice = WebDriverWait(driver, 2).until(
              EC.element_to_be_clickable((By.XPATH, '//input[@type="button" and @value="刪除"]'))
              )
              delete_error_invoice.click()
              time.sleep(2)
              alert_delete = WebDriverWait(driver, 2).until(EC.alert_is_present())
              alert_delete.accept()

              print(f'成功刪除發票{invoice_number}')
              alert_delete_check = WebDriverWait(driver, 2).until(EC.alert_is_present())
              alert_delete_check.accept()
              alert_delete_check_01 = WebDriverWait(driver, 2).until(EC.alert_is_present())
              alert_delete_check_01.accept()
              return True
          except Exception as e:
             print(f'發生錯誤:{e}')
             return False
# 初始化 WebDriver
chrome_options = Options()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
chrome_options.add_argument("--allow-insecure-localhost")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
chrome_options.add_experimental_option('useAutomationExtension', False)

service = Service("C:/webdriver/chromedriver.exe")
driver = webdriver.Chrome(options=chrome_options)

# 設定瀏覽器下載選項，避免彈出下載確認視窗
download_folder = r'C:\Users\wilsonhuang\Downloads'
options = webdriver.ChromeOptions()
options.add_argument("--safebrowsing-disable-download-protection")  # 直接關閉下載保護
options.add_experimental_option("prefs", {
    "download.default_directory": r"",
    "download.prompt_for_download": False,
    "safebrowsing.enabled": False
})

# 自動登入
driver.execute_cdp_cmd("Page.setDownloadBehavior", {
    "behavior": "allow",
    "downloadPath": r"C:\Users\wilsonhuang\Downloads"
})


warnings.filterwarnings("ignore",category=UserWarning,module="openpyxl")
env_choice = input("請選擇登入環境(1:正式區,2:測試區):")

if env_choice =="1":
   url ='https://epos.einvoice.com.tw/Welcome/Index'
   username ="WILSON"
   password = "wilson0214"
   print("您選擇[正式區]")
elif env_choice =="2":
   url = 'http://172.20.5.157:8086/'
   username ="WILSON"
   password = "0000"
else:
   print('輸入錯誤，請重新執行程式')
   exit()




driver.get(url)
wait_and_input(driver, By.ID, 'CompanyId', '23997652')
wait_and_input(driver, By.ID, 'Account', username)
wait_and_input(driver, By.ID, 'InputPassword', password)

# 手動輸入驗證碼
captcha_code = input("請輸入驗證碼並按 Enter：")
wait_and_input(driver, By.ID, 'CaptchaValue', captcha_code)
wait_and_click(driver, By.XPATH, '//button[@type="submit"]')
time.sleep(3)

try:
    while True:
     error_file_path = input("請輸入要讀取的 Excel 檔案完整路徑: ").strip()

    # 檢查檔案是否存在
     if not os.path.isfile(error_file_path):
        print("❌ 檔案不存在，請重新輸入")
        continue

    # 檢查檔名與副檔名
     file_name = os.path.basename(error_file_path)
     if not (file_name.startswith("EposError") and file_name.lower().endswith(".xlsx")):
        print("❌ 檔案名稱必須以 'EposError' 開頭，且副檔名為 .xlsx，請重新輸入")
        continue
     error_df = get_invoice_data(error_file_path)
     if error_df is not None:
        print(f"✅ 檔案讀取成功：{error_file_path}")
        # print("📄 Excel 內容如下：")
        # print(error_df)
        break

    if not error_df.empty:
             for index, row in error_df.iterrows():
                 company_id = str(row["公司統編"]) 
                 invoice_number = str(row["發票/折讓單號碼"]) 
          
    while True:
           invoice_data = get_invoice_data(error_file_path)

           if invoice_data.empty:
             print("所有發票已刪除，程式結束。")
             break

           for index, row in invoice_data.iterrows():
               company_id = str(row["公司統編"])
               invoice_number = str(row["發票/折讓單號碼"])

               result = check_invoice_count(company_id, invoice_number, invoice_data, error_file_path)

               if result == "auto_deleted":
                    print(f"✅ 發票 {invoice_number} 已自動刪除，無需人工處理")
                    # 重新讀取最新 Excel，確保下一筆是最新狀態
                    invoice_data = pd.read_excel(error_file_path, engine='openpyxl')

               elif result == "manual_check":
                   print(f"⚠️ 發票 {invoice_number} 需人工確認")

               elif result == "error":
                   print(f"❌ 發票 {invoice_number} 檢查出現錯誤")
                   traceback.print_exc()      
except Exception as e:
     print(f"發生錯誤:{e}")
     traceback.print_exc()  