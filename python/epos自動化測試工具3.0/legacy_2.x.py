from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
import warnings
import time
import os
import traceback

# ==================== 基本工具 ====================

FIXED_EXCEL_PATH = r'D:\D\wilsonhuang\Epos\EposError.xlsx'

# 選擇器常數，集中維護
SEL = {
    "menu_biz_query": (By.XPATH, '//a[contains(text(), "營業人查詢作業")]'),
    "menu_as0102": (By.XPATH, '//a[@href="/AS0102"]'),
    "btn_search_company": (By.ID, "btnSrachCom"),
    "input_company_id_query": (By.ID, "company_IdQuery"),
    "btn_company_query": (By.ID, "EAqueryQ"),
    "company_first_row": (By.XPATH, '//tbody[@id="tbCompanyId"]//tr[1]/td[1]/span'),
    "input_invoice_query": (By.ID, "invoiceNumberQuery"),
    "btn_invoice_query": (By.ID, "queryButton"),
    "invoice_rows": (By.XPATH, '//tbody[@id="tbId"]/tr'),
    "menu_ops": (By.XPATH, '//a[contains(text(), "客服維運作業")]'),
    "menu_issue_abnormal": (By.XPATH, '//a[text()="發票異常處理"]'),
    "input_ops_company": (By.XPATH, '//input[@name="uniformNoQuery"]'),
    "input_ops_invoice": (By.XPATH, '//input[@name="invoiceNumberQuery"]'),
    "btn_ops_query": (By.XPATH, '//input[@id="queryButton"]'),
    "chk_select": (By.XPATH, '//input[@type="checkbox" and @name ="selList"]'),
    "btn_delete": (By.XPATH, '//input[@type="button" and @value="刪除"]'),
}

RETRY_TIMES = int(os.getenv("EPOS_RETRY", "3"))
RETRY_SLEEP = float(os.getenv("EPOS_RETRY_SLEEP", "1.0"))

def retry_call(func, *, attempts=RETRY_TIMES, sleep=RETRY_SLEEP, desc="動作"):
    """
    通用重試：當 func 回傳值為 False / 'error' / None 時視為失敗重試
    成功條件：回傳其他值
    """
    last = None
    for i in range(1, max(1, attempts) + 1):
        last = func()
        if last not in (False, "error", None):
            if i > 1:
                print(f"✅ {desc} 第 {i} 次嘗試成功")
            return last
        if i < attempts:
            print(f"↻ {desc} 失敗，等待 {sleep}s 後重試（{i}/{attempts}）")
            time.sleep(sleep)
    print(f"❌ {desc} 重試 {attempts} 次後仍失敗")
    return last


def wait_and_click(driver, by, value, timeout=5):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return True
    except Exception as e:
        print(f"❌ 點擊元素失敗 ({value}): {e}")
        return False

def wait_and_input(driver, by, value, input_text, timeout=5):
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

def accept_all_alerts(driver, max_alerts=3, timeout=3):
    count = 0
    for _ in range(max_alerts):
        try:
            WebDriverWait(driver, timeout).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
            count += 1
            time.sleep(0.3)
        except:
            break
    return count

def get_invoice_data(path):
    try:
        if not os.path.isfile(path):
            print(f"❌ 檔案不存在: {path}")
            return pd.DataFrame()
        df = pd.read_excel(path, engine='openpyxl')
        if df.empty:
            print(f"⚠️ {path} 沒有發票資料")
        return df
    except Exception as e:
        print(f"❌ 讀取 Excel 發生錯誤: {e}")
        traceback.print_exc()
        return pd.DataFrame()

def write_excel_safely(df, output_file_path):
    try:
        df.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"📄 已儲存至 {output_file_path}")
        return True
    except Exception as e:
        print(f"❌ Excel 寫入失敗：{e}")
        traceback.print_exc()
        return False

def remove_invoice_from_dataframe(invoice_data, invoice_number, error_file_path):
    invoice_number_str = str(invoice_number).strip()
    before_count = len(invoice_data)
    invoice_data = invoice_data[
        ~invoice_data["發票/折讓單號碼"].astype(str).str.strip().eq(invoice_number_str)
    ]
    after_count = len(invoice_data)
    if before_count != after_count:
        print(f"→ Excel 更新: 原本 {before_count} 筆，現在剩 {after_count} 筆待處理")
        write_excel_safely(invoice_data, error_file_path)
    return invoice_data

# ==================== 業務流程 ====================

def check_invoice_count(driver, company_id, invoice_number, invoice_data, error_file_path):
    try:
        invoice_number_str = str(invoice_number).strip()

        if not wait_and_click(driver, *SEL["menu_biz_query"], 8):
            return "error"
        WebDriverWait(driver, 8).until(EC.presence_of_element_located(SEL["menu_as0102"]))

        if not wait_and_click(driver, *SEL["menu_as0102"], 8):
            return "error"
        WebDriverWait(driver, 8).until(EC.presence_of_element_located(SEL["btn_search_company"]))

        if not wait_and_click(driver, *SEL["btn_search_company"], 8):
            return "error"
        WebDriverWait(driver, 8).until(EC.presence_of_element_located(SEL["input_company_id_query"]))

        if not wait_and_input(driver, *SEL["input_company_id_query"], company_id, 8):
            return "error"
        print(f"✅ 輸入統編:{company_id}成功")
        if not wait_and_click(driver, *SEL["btn_company_query"], 8):
            return "error"

        company_result = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(SEL["company_first_row"]))
        driver.execute_script("arguments[0].click();", company_result)

        if not wait_and_input(driver, *SEL["input_invoice_query"], invoice_number, 8):
            return "error"
        print(f"✅ 輸入發票號碼:{invoice_number}成功")

        if not wait_and_click(driver, *SEL["btn_invoice_query"], 8):
            return "error"
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_all_elements_located(SEL["invoice_rows"]))
        except:
            pass

        rows = driver.find_elements(*SEL["invoice_rows"])
        record_count = len(rows)
        print(f"📊 發票號碼 {invoice_number} 查詢結果，共 {record_count} 筆")

        parsed = []
        for idx, row in enumerate(rows, start=1):
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) >= 10:
                status = tds[6].text.strip()
                reason = tds[9].text.strip()
                parsed.append((idx, status, reason))

        if record_count == 0:
            print(f"⚠️ 發票 {invoice_number_str} 無查詢結果，需人工確認")
            return "manual_check"

        if record_count == 1:
            idx, status, reason = parsed[0]
            if reason == "大平台回覆成功":
                print(f"✅ 發票 {invoice_number_str} 單筆成功，刪除 Excel 及系統資料")
                invoice_data = remove_invoice_from_dataframe(invoice_data, invoice_number_str, error_file_path)
                return "auto_deleted"
            else:
                print(f"⚠️ 發票 {invoice_number_str} 單筆但非成功，需要人工確認 (原因: {reason})")
                return "manual_check"

        fail_rows = [
            (idx, status, reason) for idx, status, reason in parsed
            if reason in ["大平台回覆失敗", "小平台解析失敗"]
        ]

        if not fail_rows:
            print(f"⚠️ 發票 {invoice_number_str} 沒有失敗列，需人工確認")
            return "manual_check"

        print(f"🔎 發票 {invoice_number_str} 發現 {len(fail_rows)} 筆失敗列，開始刪除...")
        for idx, status, reason in fail_rows:
            print(f"  → 刪除失敗列: 第 {idx} 列 - 狀態: {status}, 處理結果: {reason}")
            retry_call(
                lambda: delete_invoice(driver, company_id, invoice_number_str),
                desc=f"刪除發票 {invoice_number_str}",
            )

        invoice_data = remove_invoice_from_dataframe(invoice_data, invoice_number_str, error_file_path)
        return "auto_deleted"

    except Exception as e:
        print(f"❌ 檢查發票記錄失敗:{e}")
        traceback.print_exc()
        return "error"

def delete_invoice(driver, company_id, invoice_number):
    try:
        element = WebDriverWait(driver, 8).until(EC.presence_of_element_located(SEL["menu_ops"]))
        driver.execute_script(
            "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", element
        )
        driver.execute_script("arguments[0].click();", element)

        if not wait_and_click(driver, *SEL["menu_issue_abnormal"], 8):
            return False

        if not wait_and_input(driver, *SEL["input_ops_company"], company_id, 8):
            return False

        if not wait_and_input(driver, *SEL["input_ops_invoice"], invoice_number, 8):
            return False

        if not wait_and_click(driver, *SEL["btn_ops_query"], 8):
            return False

        print(f"查詢發票 {invoice_number}...中")
        rows = WebDriverWait(driver, 8).until(EC.presence_of_all_elements_located(SEL["invoice_rows"]))
        if not rows:
            print(f"⚠️ 發票 {invoice_number} 查詢無結果，無法刪除")
            return False

        checkbox = WebDriverWait(driver, 8).until(EC.presence_of_element_located(SEL["chk_select"]))
        checkbox.click()

        if not wait_and_click(driver, *SEL["btn_delete"], 8):
            return False

        accepted = accept_all_alerts(driver, max_alerts=3, timeout=3)
        print(f"✅ 成功刪除發票{invoice_number} (處理 {accepted} 個確認視窗)")
        return True
    except Exception as e:
        print(f"❌ 發生錯誤:{e}")
        traceback.print_exc()
        return False

# ==================== 啟動與登入 ====================

def init_driver(driver_path, download_dir):
    chrome_options = Options()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--safebrowsing-disable-download-protection")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False
    })
    # 環境變數可切換無頭模式：EPOS_HEADLESS=1
    if os.getenv("EPOS_HEADLESS", "").strip() in {"1", "true", "True"}:
        chrome_options.add_argument("--headless=new")

    # 方案 A: 使用指定驅動路徑（若存在）
    try:
        if driver_path and os.path.isfile(driver_path):
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": download_dir
            })
            return driver
    except Exception as e:
        print(f"⚠️ 使用指定驅動路徑失敗: {e}")

    # 方案 B: 使用 Selenium Manager（Selenium 4.6+ 內建）
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_dir
        })
        return driver
    except Exception as e:
        print(f"⚠️ 使用 Selenium Manager 下載/定位驅動失敗: {e}")

    # 方案 C: 使用 webdriver-manager 自動安裝（需要 pip install webdriver-manager）
    try:
        from webdriver_manager.chrome import ChromeDriverManager  # 延遲匯入，避免未安裝時報錯
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": download_dir
        })
        return driver
    except Exception as e:
        print("❌ 自動安裝驅動失敗。請先安裝 webdriver-manager: pip install webdriver-manager")
        print(f"詳細錯誤: {e}")
        raise

def prompt_env():
    env_choice = os.getenv("EPOS_ENV", "").strip() or input("請選擇登入環境(1:正式區,2:測試區):").strip()
    if env_choice == "1":
        return {
            "name": "正式區",
            "url": "https://epos.einvoice.com.tw/Welcome/Index",
            "username": "WILSON",
            "password": "0000"
        }
    elif env_choice == "2":
        return {
            "name": "測試區",
            "url": "http://172.20.5.157:8086/",
            "username": "WILSON",
            "password": "0000"
        }
    else:
        print("輸入錯誤，請重新執行程式")
        return None

def prompt_excel_path():
    while True:
        error_file_path = input("請輸入要讀取的 Excel 檔案完整路徑: ").strip()
        if not os.path.isfile(error_file_path):
            print("❌ 檔案不存在，請重新輸入")
            continue
        file_name = os.path.basename(error_file_path)
        if not (file_name.startswith("EposError") and file_name.lower().endswith(".xlsx")):
            print("❌ 檔案名稱必須以 'EposError' 開頭，且副檔名為 .xlsx，請重新輸入")
            continue
        df = get_invoice_data(error_file_path)
        if df is not None:
            print(f"✅ 檔案讀取成功：{error_file_path}")
            return error_file_path

def login(driver, url, username, password, company_id):
    driver.get(url)
    if not wait_and_input(driver, By.ID, 'CompanyId', company_id, 10):
        return False
    if not wait_and_input(driver, By.ID, 'Account', username, 10):
        return False
    if not wait_and_input(driver, By.ID, 'InputPassword', password, 10):
        return False
    captcha_code = input("請輸入驗證碼並按 Enter：").strip()
    if not wait_and_input(driver, By.ID, 'CaptchaValue', captcha_code, 10):
        return False
    if not wait_and_click(driver, By.XPATH, '//button[@type="submit"]', 10):
        return False
    time.sleep(2)
    return True

# ==================== 主流程 ====================

def main():
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    env = prompt_env()
    if not env:
        return
    print(f"您選擇 [{env['name']}]")

    driver_path = os.getenv("EPOS_CHROME_DRIVER", "C:/webdriver/chromedriver.exe")
    download_dir = os.getenv("EPOS_DOWNLOAD_DIR", r"C:\Users\wilsonhuang\Downloads")
    company_id = os.getenv("EPOS_COMPANY_ID", "23997652")

    try:
        driver = init_driver(driver_path, download_dir)
    except Exception as e:
        print(f"❌ 初始化瀏覽器失敗: {e}")
        return

    try:
        if not login(driver, env["url"], env["username"], env["password"], company_id):
            print("❌ 登入失敗，程式結束")
            return

        # 使用固定 Excel 路徑，若不存在則退回互動輸入
        if os.path.isfile(FIXED_EXCEL_PATH):
            error_file_path = FIXED_EXCEL_PATH
            print(f"✅ 使用固定 Excel 路徑：{error_file_path}")
        else:
            print(f"⚠️ 固定 Excel 路徑不存在：{FIXED_EXCEL_PATH}，改為手動輸入")
            error_file_path = prompt_excel_path()

        while True:
            invoice_data = get_invoice_data(error_file_path)
            if invoice_data.empty:
                print("✅ 所有發票已處理完成，程式結束。")
                break

            for _, row in invoice_data.iterrows():
                company_id = str(row["公司統編"]).strip()
                invoice_number = str(row["發票/折讓單號碼"]).strip()
                result = retry_call(
                    lambda: check_invoice_count(driver, company_id, invoice_number, invoice_data, error_file_path),
                    desc=f"發票 {invoice_number} 檢查",
                )

                if result == "auto_deleted":
                    print(f"✅ 發票 {invoice_number} 已自動刪除")
                    # 重新讀取最新 Excel，確保下一筆是最新狀態
                    invoice_data = get_invoice_data(error_file_path)
                    if invoice_data.empty:
                        break
                elif result == "manual_check":
                    print(f"⚠️ 發票 {invoice_number} 需人工確認")
                elif result == "error":
                    print(f"❌ 發票 {invoice_number} 檢查出現錯誤，略過")

    except KeyboardInterrupt:
        print("⚠️ 使用者中斷程式")
    except Exception as e:
        print(f"❌ 發生未預期錯誤: {e}")
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass
        print("✅ 程式結束")

if __name__ == "__main__":
    main()


