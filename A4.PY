import matplotlib.pyplot as plt
import math

# 設定圖片大小為 A4 比例 (約 8.27 x 11.69 inches)，但稍微調整以適應網頁顯示
fig, ax = plt.subplots(figsize=(8.27, 11.69))

# 隱藏座標軸
ax.axis('off')

# 設定行數和列數
cols = 5
rows = 7
total_nums = 35

# 繪製表格和數字
for i in range(total_nums):
    num = i + 1
    # 計算網格位置
    row = i // cols
    col = i % cols
    
    # 計算座標 (從左上角開始)
    x = col / cols
    y = 1 - (row + 1) / rows
    
    # 繪製數字
    ax.text(x + 0.5/cols, y + 0.5/rows, str(num), 
            fontsize=40, ha='center', va='center', weight='bold')
    
    # 繪製框線 (每個數字一個框)
    rect = plt.Rectangle((x, y), 1/cols, 1/rows, fill=False, color='gray', linestyle='--')
    ax.add_patch(rect)

plt.tight_layout()
plt.show()