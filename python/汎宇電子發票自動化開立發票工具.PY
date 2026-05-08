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




warnings.filterwarnings("ignore",category=UserWarning,module="openpyxl")
env_choice = input("請選擇登入環境(1:正式區,2:測試區):")

if env_choice =="1":
   url ='https://172.20.6.25/einv/Login/LoginPage.action'
   companyID='23997652'
   username ="ADMIN"
   password = "1234"
   print("您選擇[正式區]")
elif env_choice =="2":
   url = 'https://172.20.6.25/einv/Login/LoginPage.action'
   username ="ADMIN"
   password = "1234"
else:
   print('輸入錯誤，請重新執行程式')
   exit()

chrome_options = Options()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
chrome_options.add_argument("--allow-insecure-localhost")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
chrome_options.add_experimental_option('useAutomationExtension', False)

service = Service("C:/webdriver/chromedriver.exe")
driver = webdriver.Chrome(options=chrome_options)

driver.get(url)
tax_id_field = driver.find_element(By.ID, 'companyId')  
tax_id_field.send_keys('23997652')
username_field = driver.find_element(By.ID, 'userId')  
username_field.send_keys(username)
password_field = driver.find_element(By.ID, 'pass')  
password_field.send_keys(password)

captcha_field = driver.find_element(By.ID, 'securityCode')
captcha_code = input("請輸入驗證碼並按 Enter：")
captcha_field.send_keys(captcha_code)

login_btn = WebDriverWait(driver, 5).until(
    EC.element_to_be_clickable((By.XPATH, '//input[@type="image" and contains(@src, "login_btn2.png")]'))
)

# 點擊登入按鈕
login_btn.click()

element = WebDriverWait(driver, 5).until(
    EC.presence_of_element_located((By.XPATH, '//a[div[text()="B2C發票功能"]]'))
)
driver.execute_script("arguments[0].click();", element)

link = WebDriverWait(driver, 5).until(
    EC.element_to_be_clickable((By.LINK_TEXT, "開立B2C發票"))
)

# 點擊該連結
link.click()

try:
    for i in range(1, 51):
        print(f"開始開立第 {i} 張發票")

        carrier_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "add_carrierid1"))
        )
        carrier_input.clear()
        carrier_input.send_keys("/4MHA82G")

        product_id = f"{i:03d}"
        product_id_input = driver.find_element(By.NAME, "dtl_productId")
        product_id_input.clear()
        product_id_input.send_keys(product_id)

        product_name_input = driver.find_element(By.NAME, "dtl_productName")
        product_name_input.clear()
        product_name_input.send_keys("測試商品")

        unit_price_input = driver.find_element(By.NAME, "dtl_unitPrice")
        unit_price_input.clear()
        unit_price_input.send_keys("100")

        unit_price_input = driver.find_element(By.NAME, "dtl_qty")
        unit_price_input.clear()
        unit_price_input.send_keys("1")

        save_btn = driver.find_element(By.ID, "saveBt")
        save_btn.click()

        print(f"第 {i} 張發票已送出，等待頁面刷新...") 
        WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()     

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "add_carrierid1"))
        )

        time.sleep(1)

    print("完成 {i} 張發票開立。")

except Exception as e:
    print("程式執行時發生錯誤，詳情如下：")
    traceback.print_exc()
    input("發生錯誤，請查看上方錯誤訊息，按 Enter 結束程式...")
