# SQL UPDATE 語法生成工具

## 功能說明
自動生成 `UPDATE XML_MESSAGE` 的 SQL 語法，並使用當前時間作為 `UPDATE_DTM`。

## 使用方法

### 1. 準備檔案名稱列表
在 `data/filenames.txt` 中填入要更新的檔案名稱，每行一個：
```
G0401_00517179_ZL68724180000001_2026031160424666-POS.xml
G0401_00517179_ZL68724181000002_2026031160425777-POS.xml
G0401_00517179_ZL68724182000003_2026031160426888-POS.xml
```

### 2. 執行程式
```bash
python SQL.PY
```

### 3. 查看結果
- 螢幕會顯示所有生成的 SQL 語句
- SQL 語句會自動儲存到 `output/generated_sql.sql`
- 可選擇複製到剪貼簿（需安裝 pyperclip）

## 輸出範例
```sql
UPDATE XML_MESSAGE SET status='2', count='0', send_status='0', ip_port='', error_code='00000', UPDATE_DTM='20260506113000' WHERE file_name='G0401_00517179_ZL68724180000001_2026031160424666-POS.xml';
```

## 設定說明

### 在 SQL.PY 中可以修改：

1. **輸入檔案路徑**
```python
INPUT_FILE = r"D:\D\wilsonhuang\Worktime\python\自動化語法產生程式\data\filenames.txt"
```

2. **輸出檔案路徑**
```python
OUTPUT_FILE = r"D:\D\wilsonhuang\Worktime\python\自動化語法產生程式\output\generated_sql.sql"
```

3. **SQL 參數設定**
```python
SQL_TEMPLATE = {
    'status': '2',
    'count': '0',
    'send_status': '0',
    'ip_port': '',
    'error_code': '00000'
}
```

## 時間格式
- `UPDATE_DTM` 會自動使用當前時間
- 格式：`YYYYMMDDHHmmss`
- 例如：`20260506113000` (2026年5月6日 11:30:00)

## 可選功能
安裝 pyperclip 後可以直接複製到剪貼簿：
```bash
pip install pyperclip
```
