let year123 = document.getElementById("year123")
let btn = document.getElementById('btn')

btn.addEventListener('click',e=>{
    const  calulateValue = document.getElementById('calulate').value
    const   Year = year123.value
    const total = Math.floor(calulateValue * (Year*12) * 1.025)
    const interest = Math.floor(total  - (calulateValue* (Year*12)) )
    const  totalPrice = document.getElementById('totalPrice')
    const  interestPrice = document.getElementById('interestPrice')
    totalPrice.innerText = total
    interestPrice.innerText =  interest
    
    
})









function createValue(num,value,fatherlabel,label){
    for(let i =value ;i<=num;i++)
        {
            const objValue = document.createElement(label)
            objValue.innerText = i
            fatherlabel.appendChild(objValue)
        }
}

createValue(12,1,year123,'option')