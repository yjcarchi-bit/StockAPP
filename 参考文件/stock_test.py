import efinance as ef
bill = ef.stock.get_today_bill('600519')
print(bill)
