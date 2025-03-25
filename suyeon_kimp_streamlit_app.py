# 수연이 자동화 앱 (Binance 연결은 루프 진입 시점에만!)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import requests
import matplotlib
import json
import os
import random

matplotlib.rcParams['font.family'] = 'AppleGothic'
matplotlib.rcParams['axes.unicode_minus'] = False

# 실시간 환율 가져오기
def get_realtime_fx():
    try:
        response = requests.get("https://api.manana.kr/exchange/rate/KRW/USD.json")
        data = response.json()[0]
        return float(data['rate']), datetime.strptime(data['date'], "%Y-%m-%d")
    except:
        return 1450.0, datetime.today()

# 실시간 시세
def get_binance_price():
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        return float(response.json()["price"])
    except:
        return None

def get_upbit_price():
    try:
        response = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC")
        return float(response.json()[0]["trade_price"])
    except:
        return None

# 텔레그램 알림
def send_telegram_alert(message):
    TELEGRAM_TOKEN = "7896712003:AAFfS_bwSQaXcqtw0fbUdWa40fOEdxucYbI"
    CHAT_ID = "7896712003"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

# Binance 주문 함수 → 루프 실행 시점에만 초기화
def place_market_buy(symbol="BTCUSDT", quantity=0.001):
    from binance.client import Client
    try:
        BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
        BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
        if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
            return "❌ Binance 키가 설정되지 않았습니다.", None
        client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
        order = client.order_market_buy(symbol=symbol, quantity=quantity)
        return "✅ 실전 주문 성공", order
    except Exception as e:
        return f"❌ 주문 실패: {str(e)}", None

# 상태 초기화
if "loop_data" not in st.session_state:
    st.session_state.loop_data = []
    st.session_state.capital = 33000000
    st.session_state.loops = 0
if "last_run_date" not in st.session_state:
    st.session_state.last_run_date = None
    st.session_state.loop_executed = False

# 자정 기준 리셋
today = date.today()
if st.session_state.last_run_date != today:
    st.session_state.loop_executed = False
    st.session_state.last_run_date = today

# 앱 시작
st.set_page_config(page_title="수연이 자동화", layout="centered")
st.title("💖 수연이 실전 자동 루프 시스템")

# 실시간 데이터
krw_rate, fx_time = get_realtime_fx()
krw_buy = krw_rate * 1.0005
krw_sell = krw_rate
binance_price = get_binance_price()
upbit_price = get_upbit_price()

st.subheader(f"📈 실시간 시세 & 환율 (기준일: {fx_time.strftime('%Y-%m-%d')})")
if binance_price and upbit_price:
    st.metric("Binance BTC", f"${binance_price:,.2f}")
    st.metric("Upbit BTC", f"₩{int(upbit_price):,}")
    kimp = ((upbit_price - binance_price * krw_buy) / (binance_price * krw_buy)) * 100
    st.metric("김치프리미엄", f"{kimp:.2f}%")
else:
    kimp = 0
    st.warning("실시간 시세 로딩 실패")

# 수수료
fee_fx = st.number_input("환전 수수료율 (%)", value=0.05) / 100
fee_binance = st.number_input("Binance 거래 수수료율 (%)", value=0.075) / 100
fee_upbit = st.number_input("Upbit 매도 수수료율 (%)", value=0.05) / 100

# 루프 시뮬레이션
st.subheader("💸 루프 수익 시뮬레이션")
initial_krw = st.number_input("₩ 보유 원화 입력", value=33000000)
if binance_price and upbit_price:
    usd_after = (initial_krw / krw_buy) * (1 - fee_fx)
    btc_buy = (usd_after / binance_price) * (1 - fee_binance)
    krw_out = btc_buy * upbit_price * (1 - fee_upbit)
    profit = krw_out - initial_krw
    real_rate = profit / initial_krw
    st.metric("1️⃣ 환전 후 달러", f"${usd_after:,.2f}")
    st.metric("2️⃣ Binance BTC 매입량", f"{btc_buy:.6f} BTC")
    st.metric("3️⃣ 업비트 원화 수령액", f"₩{int(krw_out):,}")
    st.metric("💰 루프 수익", f"₩{int(profit):,}")
    st.metric("📈 실질 수익률", f"{real_rate*100:.2f}%")
else:
    st.error("시세 불러오기 실패")

# 조건 감지 실행
st.subheader("🔥 자동 루프 감지 & 실행")
kimp_rate = st.number_input("김프 수익률 (%)", value=3.0, step=0.01)
fee_total = fee_fx + fee_binance + fee_upbit
real_rate = (kimp_rate - fee_total * 100) / 100
simulation_mode = st.toggle("🧪 시뮬레이션 모드", value=True)

if real_rate >= 0.02 and (krw_buy - krw_sell) <= 10:
    if not st.session_state.loop_executed:
        st.success("✅ 조건 만족: 루프 실행")
        new_cap = st.session_state.capital * (1 + real_rate)
        st.session_state.loops += 1
        st.session_state.capital = new_cap
        st.session_state.loop_data.append({
            "회전": st.session_state.loops,
            "시간": datetime.now().strftime("%H:%M:%S"),
            "수익률": round(real_rate * 100, 2),
            "자산(₩)": int(new_cap)
        })
        st.session_state.loop_executed = True
        send_telegram_alert(f"✅ 루프 #{st.session_state.loops} 실행됨! 수익률 {real_rate*100:.2f}% 자산 ₩{int(new_cap):,}")

        # Binance 주문은 이 시점에만!
        if not simulation_mode:
            msg, result = place_market_buy()
            st.write(msg)
else:
    st.info("복합 조건 미충족 → 대기 중")

# 자산 리포트
st.subheader("📊 누적 자산 리포트")
st.metric("누적 루프 수", st.session_state.loops)
st.metric("누적 자산 (₩)", f"{int(st.session_state.capital):,}")
if st.session_state.loop_data:
    df = pd.DataFrame(st.session_state.loop_data)
    fig, ax = plt.subplots()
    ax.plot(df["회전"], df["자산(₩)"], marker='o', color='hotpink')
    ax.set_xlabel("회전")
    ax.set_ylabel("자산(₩)")
    ax.grid(True)
    st.pyplot(fig)
    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 루프 로그 다운로드", csv, "loop_record.csv")

