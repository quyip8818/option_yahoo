import time
import webbrowser

symbol_str = """
AG
HL
PAAS
KGC
NEM
BTG
AEM
B"""

symbols = [s.strip() for s in symbol_str.split()]

for symbol in symbols:
    url = f"https://optionstrat.com/build/long-call/{symbol}"
    webbrowser.open(url)
    time.sleep(0.5)
