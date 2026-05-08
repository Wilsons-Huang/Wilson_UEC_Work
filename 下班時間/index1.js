let dateElement = document.getElementById('date');
let weekendtime = document.getElementById('weekendtime');
let Yearday = document.getElementById('Yearday')
let countdownInterval;  
let day2 = new Date()
Yearday.innerHTML = `${day2.getFullYear()}/${day2.getMonth()+1}/${day2.getDate()}`



let day = new Date().getDay();
if (day >= 1 && day < 5) {
    weekendtime.innerHTML = `還有${5 - day}天放假!`;
} else {
    weekendtime.innerHTML = '終於要放假了...';
}

function populateTimeOptions() {
    let hourSelect = document.getElementById('hourSelect');
    let minuteSelect = document.getElementById('minuteSelect');

    for (let i = 0; i <= 24; i++) {
        let option = document.createElement("option");
        option.value = i;
        option.text = i;
        hourSelect.appendChild(option);
    }


    for (let i = 0; i < 60; i++) {
        let option = document.createElement("option");
        option.value = i;
        option.text = i < 10 ? '0' + i : i; // 格式化分鐘數
        minuteSelect.appendChild(option);
    }
}

populateTimeOptions(); 
// 倒數計時邏輯
function updateCountdown(endHour, endMinute) {
    let now = new Date();
    let currentHour = now.getHours();
    let currentMinute = now.getMinutes();
    let currentSecond = now.getSeconds();

    let remainingHours = endHour - currentHour;
    let remainingMinutes = endMinute - currentMinute;
    let remainingSeconds = 0 - currentSecond;

    if (remainingSeconds < 0) {
        remainingSeconds += 60;
        remainingMinutes -= 1;
    }
    if (remainingMinutes < 0) {
        remainingMinutes += 60;
        remainingHours -= 1;
    }

    if (remainingHours < 0 || (remainingHours === 0 && remainingMinutes === 0 && remainingSeconds === 0)) {
        dateElement.innerHTML = "已下班";
        alert('已下班!!')
        clearInterval(countdownInterval); // 倒數結束時停止計時器
    } else {
        dateElement.innerHTML = `下班倒數：${remainingHours}時 ${remainingMinutes}分 ${remainingSeconds}秒`;
    }
}

// 取得選擇的下班時間
function getSelectedTime() {
    let selectedHour = parseInt(document.getElementById('hourSelect').value);
    let selectedMinute = parseInt(document.getElementById('minuteSelect').value);
    return { selectedHour, selectedMinute };
}

// 開始倒數並清除舊的倒數計時器
function startCountdown() {
    clearInterval(countdownInterval); // 清除舊的計時器

    let { selectedHour, selectedMinute } = getSelectedTime();
    countdownInterval = setInterval(() => updateCountdown(selectedHour, selectedMinute), 1000);
}

document.getElementById('hourSelect').addEventListener('change', startCountdown);
document.getElementById('minuteSelect').addEventListener('change', startCountdown);