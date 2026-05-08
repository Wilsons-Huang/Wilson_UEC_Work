from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import json
import os
import time
import traceback
import warnings

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = BASE_DIR / "downloads"
DEFAULT_EXCEL_PATH = DATA_DIR / "EposError.xlsx"
DEBUG_LOG_PATH = BASE_DIR / "debug-79f104.log"
DEBUG_SESSION_ID = "79f104"

RETRY_TIMES = int(os.getenv("EPOS_RETRY", "3"))
RETRY_SLEEP = float(os.getenv("EPOS_RETRY_SLEEP", "0.6"))
SHORT_TIMEOUT = int(os.getenv("EPOS_SHORT_TIMEOUT", "6"))
LONG_TIMEOUT = int(os.getenv("EPOS_LONG_TIMEOUT", "10"))
SAVE_EVERY_N_AUTODELETE = int(os.getenv("EPOS_SAVE_EVERY_N_AUTODELETE", "5"))
CAPTCHA_RELOGIN_MAX_TRIES = int(os.getenv("EPOS_CAPTCHA_RELOGIN_MAX_TRIES", "5"))


def debug_log(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "pre-fix") -> None:
    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        try:
            # 備援路徑：以執行時工作目錄輸出，避免路徑編碼或權限導致主路徑失敗
            with Path("debug-79f104.log").open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as fallback_exc:
            print(f"[DEBUG_LOG_FAIL] {exc} | fallback: {fallback_exc}")


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


@dataclass
class Environment:
    name: str
    url: str
    username: str
    password: str


class EposAutomationRunner:
    def __init__(self, driver: WebDriver, company_id_default: str):
        self.driver = driver
        self.company_id_default = self.normalize_company_id(company_id_default)
        self._opened_biz_page = False
        self._opened_ops_page = False
        self._biz_selected_company_id: str = ""

    @staticmethod
    def normalize_company_id(company_id: object) -> str:
        raw_text = str(company_id).strip()
        digits = "".join(ch for ch in raw_text if ch.isdigit())
        normalized = digits.zfill(8) if digits else ""
        if normalized and normalized != raw_text:
            print(f"ℹ️ 統編正規化: 原始[{raw_text}] -> 補零後[{normalized}]")
        return normalized

    @staticmethod
    def normalize_invoice_no(invoice_number: object) -> str:
        return str(invoice_number).strip()

    def wait_and_click(self, locator: tuple[str, str], timeout: int = SHORT_TIMEOUT) -> bool:
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(locator))
            element.click()
            return True
        except Exception as exc:
            print(f"❌ 點擊失敗 {locator}: {exc}")
            return False

    def wait_and_input(self, locator: tuple[str, str], value: str, timeout: int = SHORT_TIMEOUT) -> bool:
        try:
            element = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
            element.clear()
            element.send_keys(value)
            return True
        except Exception as exc:
            print(f"❌ 輸入失敗 {locator}: {exc}")
            return False

    def accept_all_alerts(self, max_alerts: int = 3, timeout: int = 2) -> int:
        count = 0
        for _ in range(max_alerts):
            try:
                WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
                self.driver.switch_to.alert.accept()
                count += 1
                time.sleep(0.2)
            except Exception:
                break
        return count

    def open_business_query_page(self) -> bool:
        # 與 legacy 一致：每次查詢前都強制切回營業人查詢頁，避免停留在客服維運作業
        if not self.wait_and_click(SEL["menu_biz_query"], LONG_TIMEOUT):
            return False
        if not self.wait_and_click(SEL["menu_as0102"], LONG_TIMEOUT):
            return False
        WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_element_located(SEL["btn_search_company"]))
        self._opened_biz_page = True
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:open_business_query_page",
            "Opened business query page",
            {"currentUrl": self.driver.current_url, "openedBizPage": self._opened_biz_page},
            "H1",
        )
        # endregion
        return True

    def open_ops_page(self) -> bool:

        menu_ops = WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_element_located(SEL["menu_ops"]))
        self.driver.execute_script(
            "arguments[0].style.display='block';arguments[0].style.visibility='visible';", menu_ops
        )
        self.driver.execute_script("arguments[0].click();", menu_ops)
        if not self.wait_and_click(SEL["menu_issue_abnormal"], LONG_TIMEOUT):
            return False
        WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_element_located(SEL["input_ops_company"]))
        self._opened_ops_page = True
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:open_ops_page:ready",
            "Ops page ready",
            {"currentUrl": self.driver.current_url, "openedOpsPage": self._opened_ops_page},
            "H2",
            run_id="post-fix",
        )
        # endregion
        return True

    def query_invoice_rows(self, company_id: str, invoice_number: str) -> Optional[list[tuple[int, str, str]]]:
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:query_invoice_rows:start",
            "Start invoice query",
            {"companyId": company_id, "invoiceNumber": invoice_number, "currentUrl": self.driver.current_url},
            "H1",
        )
        # endregion
        if not self.open_business_query_page():
            return None
        if not self.wait_and_click(SEL["btn_search_company"], LONG_TIMEOUT):
            return None
        if not self.wait_and_input(SEL["input_company_id_query"], company_id, LONG_TIMEOUT):
            return None
        if not self.wait_and_click(SEL["btn_company_query"], LONG_TIMEOUT):
            return None
        company_row = WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.element_to_be_clickable(SEL["company_first_row"]))
        self.driver.execute_script("arguments[0].click();", company_row)
        self._biz_selected_company_id = company_id
        if not self.wait_and_input(SEL["input_invoice_query"], invoice_number, LONG_TIMEOUT):
            return None
        if not self.wait_and_click(SEL["btn_invoice_query"], LONG_TIMEOUT):
            return None

        try:
            WebDriverWait(self.driver, SHORT_TIMEOUT).until(EC.presence_of_all_elements_located(SEL["invoice_rows"]))
        except Exception:
            pass

        # 以 JS 一次擷取所有列資料，避免大量 Selenium element round-trip
        rows_data = self.driver.execute_script(
            """
            const rows = Array.from(document.querySelectorAll('#tbId tr'));
            return rows.map((row, i) => {
              const tds = row.querySelectorAll('td');
              if (tds.length < 10) return null;
              return [i + 1, (tds[6].innerText || '').trim(), (tds[9].innerText || '').trim()];
            }).filter(Boolean);
            """
        )
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:query_invoice_rows:rows",
            "Fetched invoice rows",
            {"companyId": company_id, "invoiceNumber": invoice_number, "rowCount": len(rows_data), "rows": rows_data[:5]},
            "H3",
        )
        # endregion
        return [(int(idx), str(status), str(reason)) for idx, status, reason in rows_data]

    def delete_invoice(self, company_id: str, invoice_number: str) -> bool:
        # 刪除頁面查詢統編要補到 8 碼，避免搜尋不到資料
        company_id_8 = self.normalize_company_id(company_id)
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:delete_invoice:start",
            "Start delete invoice",
            {"companyId": company_id_8, "invoiceNumber": invoice_number, "currentUrl": self.driver.current_url},
            "H2",
        )
        # endregion
        if not self.open_ops_page():
            return False
        if not self.wait_and_input(SEL["input_ops_company"], company_id_8, LONG_TIMEOUT):
            return False
        if not self.wait_and_input(SEL["input_ops_invoice"], invoice_number, LONG_TIMEOUT):
            return False
        if not self.wait_and_click(SEL["btn_ops_query"], LONG_TIMEOUT):
            return False

        rows = WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_all_elements_located(SEL["invoice_rows"]))
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:delete_invoice:query_result",
            "Delete page query result",
            {"invoiceNumber": invoice_number, "rowCount": len(rows)},
            "H2",
        )
        # endregion
        if not rows:
            print(f"⚠️ 發票 {invoice_number} 查無資料，無法刪除")
            return False

        checkbox = WebDriverWait(self.driver, LONG_TIMEOUT).until(EC.presence_of_element_located(SEL["chk_select"]))
        checkbox.click()
        if not self.wait_and_click(SEL["btn_delete"], LONG_TIMEOUT):
            return False
        accepted = self.accept_all_alerts(max_alerts=3, timeout=3)
        print(f"✅ 已刪除發票 {invoice_number}，確認視窗 {accepted} 次")
        return True

    def check_and_process_invoice(self, company_id: str, invoice_number: str) -> str:
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:check_and_process_invoice:start",
            "Start process invoice",
            {"companyId": company_id, "invoiceNumber": invoice_number, "currentUrl": self.driver.current_url},
            "H4",
        )
        # endregion
        rows = self.query_invoice_rows(company_id, invoice_number)
        if rows is None:
            # region agent log
            debug_log(
                "Epos自動化測試工具3.0.py:check_and_process_invoice:error",
                "Query rows returned None",
                {"companyId": company_id, "invoiceNumber": invoice_number},
                "H1",
            )
            # endregion
            return "error"
        if not rows:
            print(f"⚠️ 發票 {invoice_number} 無查詢結果，需人工確認")
            return "manual_check"
        if len(rows) == 1:
            _, _, reason = rows[0]
            if reason == "大平台回覆成功":
                return "auto_deleted"
            return "manual_check"

        fail_rows = [item for item in rows if item[2] in {"大平台回覆失敗", "小平台解析失敗"}]
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:check_and_process_invoice:decision",
            "Decision for multi rows",
            {
                "invoiceNumber": invoice_number,
                "totalRows": len(rows),
                "failRows": len(fail_rows),
                "reasons": [reason for _, _, reason in rows],
            },
            "H3",
        )
        # endregion
        if not fail_rows:
            return "manual_check"

        print(f"🔎 發票 {invoice_number} 找到 {len(fail_rows)} 筆失敗列，開始刪除")
        for _, _, reason in fail_rows:
            print(f"  → 刪除原因: {reason}")
            if not retry_call(lambda: self.delete_invoice(company_id, invoice_number), desc=f"刪除 {invoice_number}"):
                return "error"
        return "auto_deleted"


def retry_call(func: Callable[[], object], attempts: int = RETRY_TIMES, sleep: float = RETRY_SLEEP, desc: str = "動作"):
    last = None
    tries = max(1, attempts)
    for idx in range(1, tries + 1):
        last = func()
        if last not in (False, None, "error"):
            if idx > 1:
                print(f"✅ {desc} 第 {idx} 次成功")
            return last
        if idx < tries:
            print(f"↻ {desc} 失敗，{sleep}s 後重試 ({idx}/{tries})")
            time.sleep(sleep)
    print(f"❌ {desc} 重試 {tries} 次仍失敗")
    return last


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_invoice_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        print(f"❌ Excel 不存在: {path}")
        return pd.DataFrame()
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as exc:
        print(f"❌ 讀取 Excel 錯誤: {exc}")
        traceback.print_exc()
        return pd.DataFrame()

    required_cols = {"公司統編", "發票/折讓單號碼"}
    if not required_cols.issubset(set(df.columns)):
        print("❌ Excel 缺少必要欄位: 公司統編 / 發票/折讓單號碼")
        return pd.DataFrame()

    df = df.dropna(subset=["公司統編", "發票/折讓單號碼"]).copy()
    return df


def write_invoice_data(df: pd.DataFrame, path: Path) -> bool:
    try:
        df.to_excel(path, index=False, engine="openpyxl")
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:write_invoice_data:success",
            "Excel write success",
            {"path": str(path), "rows": len(df)},
            "H5",
            run_id="post-fix",
        )
        # endregion
        return True
    except PermissionError as exc:
        alt_path = path.with_name(f"{path.stem}.updated{path.suffix}")
        print(f"⚠️ Excel 檔案被占用，改寫入備援檔案: {alt_path}")
        try:
            df.to_excel(alt_path, index=False, engine="openpyxl")
            # region agent log
            debug_log(
                "Epos自動化測試工具3.0.py:write_invoice_data:fallback",
                "Excel locked, wrote fallback file",
                {"originalPath": str(path), "fallbackPath": str(alt_path), "rows": len(df), "error": str(exc)},
                "H5",
                run_id="post-fix",
            )
            # endregion
            return True
        except Exception as fallback_exc:
            print(f"❌ 備援檔案寫入失敗: {fallback_exc}")
            traceback.print_exc()
            # region agent log
            debug_log(
                "Epos自動化測試工具3.0.py:write_invoice_data:fallback_fail",
                "Excel fallback write failed",
                {"originalPath": str(path), "fallbackPath": str(alt_path), "error": str(fallback_exc)},
                "H5",
                run_id="post-fix",
            )
            # endregion
            return False
    except Exception as exc:
        print(f"❌ Excel 寫入失敗: {exc}")
        traceback.print_exc()
        # region agent log
        debug_log(
            "Epos自動化測試工具3.0.py:write_invoice_data:fail",
            "Excel write failed",
            {"path": str(path), "error": str(exc), "rows": len(df)},
            "H5",
            run_id="post-fix",
        )
        # endregion
        return False


def prompt_env() -> Optional[Environment]:
    choice = os.getenv("EPOS_ENV", "").strip() or input("請選擇登入環境(1:正式區,2:測試區):").strip()
    if choice == "1":
        return Environment("正式區", "https://epos.einvoice.com.tw/Welcome/Index", "WILSON", "0000")
    if choice == "2":
        return Environment("測試區", "http://172.20.5.157:8086/", "WILSON", "0000")
    print("❌ 環境輸入錯誤")
    return None


def prompt_excel_path() -> Path:
    env_value = os.getenv("EPOS_EXCEL_PATH", "").strip()
    if env_value:
        return Path(env_value)
    return DEFAULT_EXCEL_PATH


def init_driver(driver_path: str, download_dir: str) -> WebDriver:
    chrome_options = Options()
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--safebrowsing-disable-download-protection")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "safebrowsing.enabled": False,
        },
    )
    if os.getenv("EPOS_HEADLESS", "").strip().lower() in {"1", "true"}:
        chrome_options.add_argument("--headless=new")

    if driver_path and Path(driver_path).is_file():
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": download_dir})
    return driver


def detect_login_failure_reason(driver: WebDriver) -> str:
    try:
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        alert_text = driver.switch_to.alert.text.strip()
        driver.switch_to.alert.accept()
        if "驗證碼" in alert_text:
            return "captcha_error"
    except Exception:
        pass

    page_text = driver.page_source
    captcha_keywords = ("驗證碼", "captcha")
    failed_keywords = ("錯誤", "失敗", "不正確", "error", "invalid")
    if any(k in page_text for k in captcha_keywords) and any(k in page_text.lower() for k in failed_keywords):
        return "captcha_error"
    return "login_failed"


def login(driver: WebDriver, env: Environment, company_id: str) -> tuple[bool, str]:
    driver.get(env.url)
    runner = EposAutomationRunner(driver, company_id)
    if not runner.wait_and_input((By.ID, "CompanyId"), company_id, LONG_TIMEOUT):
        return False, "login_failed"
    if not runner.wait_and_input((By.ID, "Account"), env.username, LONG_TIMEOUT):
        return False, "login_failed"
    if not runner.wait_and_input((By.ID, "InputPassword"), env.password, LONG_TIMEOUT):
        return False, "login_failed"
    captcha = input("請輸入驗證碼並按 Enter：").strip()
    if not runner.wait_and_input((By.ID, "CaptchaValue"), captcha, LONG_TIMEOUT):
        return False, "login_failed"
    if not runner.wait_and_click((By.XPATH, '//button[@type="submit"]'), LONG_TIMEOUT):
        return False, "login_failed"
    time.sleep(1.2)

    # 若登入頁欄位仍存在，視為登入失敗（常見為驗證碼錯誤）
    try:
        WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.ID, "CompanyId")))
        return False, detect_login_failure_reason(driver)
    except Exception:
        return True, "success"


def main() -> None:
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    ensure_runtime_dirs()

    env = prompt_env()
    if not env:
        return
    print(f"✅ 已選擇: {env.name}")

    excel_path = prompt_excel_path()
    if not excel_path.is_absolute():
        excel_path = (BASE_DIR / excel_path).resolve()
    print(f"📄 本次處理 Excel: {excel_path}")

    initial_df = get_invoice_data(excel_path)
    if initial_df.empty:
        print("⚠️ 沒有可處理資料，程式結束")
        return

    driver_path = os.getenv("EPOS_CHROME_DRIVER", "C:/webdriver/chromedriver.exe")
    company_id_default = EposAutomationRunner.normalize_company_id("23997652")
    download_path = os.getenv("EPOS_DOWNLOAD_DIR", str(DOWNLOAD_DIR))

    driver: Optional[WebDriver] = None

    try:
        login_ok = False
        for login_try in range(1, max(1, CAPTCHA_RELOGIN_MAX_TRIES) + 1):
            try:
                driver = init_driver(driver_path, download_path)
            except Exception as exc:
                print(f"❌ 初始化瀏覽器失敗: {exc}")
                traceback.print_exc()
                return

            login_ok, reason = login(driver, env, company_id_default)
            if login_ok:
                break

            try:
                driver.quit()
            except Exception:
                pass
            driver = None

            if reason == "captcha_error" and login_try < CAPTCHA_RELOGIN_MAX_TRIES:
                print(f"⚠️ 驗證碼錯誤，將重新開啟瀏覽器後再試一次 ({login_try}/{CAPTCHA_RELOGIN_MAX_TRIES})")
                continue

            print("❌ 登入失敗")
            return

        if not login_ok or driver is None:
            print("❌ 登入失敗")
            return

        runner = EposAutomationRunner(driver, company_id_default)
        pending_df = initial_df.copy()
        processed = 0
        auto_deleted = 0
        manual_check = 0
        dirty_excel = False

        for company_raw, invoice_raw in zip(
            initial_df["公司統編"].tolist(),
            initial_df["發票/折讓單號碼"].tolist(),
        ):
            company_id = runner.normalize_company_id(company_raw)
            invoice_no = runner.normalize_invoice_no(invoice_raw)
            result = retry_call(lambda: runner.check_and_process_invoice(company_id, invoice_no), desc=f"檢查 {invoice_no}")

            processed += 1
            if result == "auto_deleted":
                auto_deleted += 1
                pending_df = pending_df[
                    ~pending_df["發票/折讓單號碼"].astype(str).str.strip().eq(invoice_no)
                ].copy()
                dirty_excel = True
                # 每 N 筆或最後一筆再寫檔，減少 I/O 次數
                if auto_deleted % max(1, SAVE_EVERY_N_AUTODELETE) == 0:
                    write_invoice_data(pending_df, excel_path)
                    dirty_excel = False
                print(f"✅ 已移除發票 {invoice_no}，剩餘 {len(pending_df)} 筆")
            elif result == "manual_check":
                manual_check += 1
                print(f"⚠️ 發票 {invoice_no} 需人工確認")
            else:
                print(f"❌ 發票 {invoice_no} 處理失敗")

        if dirty_excel:
            write_invoice_data(pending_df, excel_path)

        print("========== 執行完成 ==========")
        print(f"處理總筆數: {processed}")
        print(f"自動刪除: {auto_deleted}")
        print(f"人工確認: {manual_check}")
        print(f"待處理剩餘: {len(pending_df)}")
    except KeyboardInterrupt:
        print("⚠️ 使用者中斷程式")
    except Exception as exc:
        print(f"❌ 程式執行發生錯誤: {exc}")
        traceback.print_exc()
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            pass
        print("✅ 程式結束")


if __name__ == "__main__":
    main()
