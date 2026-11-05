# -*- coding: utf-8 -*-
"""
ETF_Coin — 가계자산 투자설계 11·12주차 수업용 체험 앱
  ① 레버리지 volatility drag 시뮬레이터
  ② 커버드콜 복권 시뮬레이터
  ③ DeFi 수익 분해 계산기

모든 계산은 브라우저 세션 안에서만 일어납니다.
데이터베이스도, 외부 네트워크 호출도 없습니다.
"""

import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ETF_Coin 체험", page_icon="📊", layout="wide")

# ----------------------------------------------------------------------
# 공통 스타일
# ----------------------------------------------------------------------
st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1150px;}
  /* 휴대폰 화면 대응 */
  @media (max-width: 640px) {
    .block-container {padding-top: 1rem; padding-left: 1rem; padding-right: 1rem;}
    h1 {font-size: 1.5rem !important; line-height: 1.3 !important;}
    h2, h3 {font-size: 1.15rem !important;}
    .big {font-size: 1.05rem !important;}
    .boxed {padding: 10px 12px;}
    [data-testid="stMetricValue"] {font-size: 1.25rem !important;}
    [data-testid="stMetricLabel"] {font-size: 0.78rem !important;}
  }
  .big {font-size: 1.45rem; font-weight: 700; line-height: 1.5;}
  .mid {font-size: 1.1rem; font-weight: 600;}
  .muted {color: #666; font-size: 0.9rem;}
  .boxed {background:#F4F3EC; border:1px solid #CFC7B0; border-radius:6px;
          padding:14px 18px; margin:8px 0 14px 0;}
  .brick {color:#9C4A3C;}
  .blue  {color:#41617A;}
  .olive {color:#6E7B4F;}
</style>
""", unsafe_allow_html=True)


def box(html: str):
    st.markdown(f'<div class="boxed">{html}</div>', unsafe_allow_html=True)


def pct(x: float, digits: int = 2) -> str:
    return f"{x:+.{digits}f}%"


def color_of(x: float) -> str:
    return "brick" if x < 0 else "blue"


st.title("ETF_Coin")
st.markdown("#### 직접 계산해 보는 시간")
st.caption("가계자산 투자설계 · 11주차 / 12주차 수업용. 숫자를 직접 움직여 보세요.")

tab1, tab2, tab3 = st.tabs(["① 레버리지", "② 커버드콜", "③ DeFi"])

# ======================================================================
# ① 레버리지 volatility drag
# ======================================================================
with tab1:
    st.subheader("① 레버리지 ETF는 왜 '기간 2배'가 아닌가")
    box("지수의 <b>일간</b> 수익률에 배율을 곱해 매일 다시 맞춥니다. "
        "그 결과가 기간 전체로는 어떻게 되는지 직접 만들어 보세요.")

    c1, c2 = st.columns([1, 2])

    with c1:
        pattern = st.radio(
            "지수가 어떻게 움직이나",
            ["횡보 (출렁임)", "상승 추세", "하락 추세", "급락 후 회복", "직접 입력"],
            index=0,
        )
        days = st.slider("기간 (거래일)", 10, 250, 60, step=10)
        move = st.slider("하루 변동폭 (%)", 0.5, 10.0, 3.0, step=0.5,
                         help="횡보는 ±이 값만큼 번갈아, 추세는 매일 같은 방향으로 움직입니다.")
        picks = st.multiselect(
            "비교할 배율",
            ["1배 (지수)", "2배", "3배", "-1배 (인버스)", "-2배 (곱버스)"],
            default=["1배 (지수)", "2배", "3배"],
        )
        custom = ""
        if pattern == "직접 입력":
            custom = st.text_area(
                "일별 등락률을 쉼표로 (%)",
                "5, -3, 2, -6, 4, 1, -2, 3, -5, 2",
                height=90,
            )

    # ---- 일별 지수 등락률 만들기 -------------------------------------
    def daily_returns() -> list:
        m = move / 100.0
        if pattern == "횡보 (출렁임)":
            return [m if i % 2 == 0 else -m for i in range(days)]
        if pattern == "상승 추세":
            return [m] * days
        if pattern == "하락 추세":
            return [-m] * days
        if pattern == "급락 후 회복":
            half = days // 2
            down = -m * 2
            # 절반 동안 하락한 뒤, 나머지 기간에 원래 수준으로 정확히 복귀
            drop = (1 + down) ** half
            up = (1.0 / drop) ** (1.0 / max(days - half, 1)) - 1
            return [down] * half + [up] * (days - half)
        # 직접 입력
        out = []
        for piece in custom.replace("\n", ",").split(","):
            piece = piece.strip().replace("%", "")
            if not piece:
                continue
            try:
                out.append(float(piece) / 100.0)
            except ValueError:
                pass
        return out or [0.0]

    rets = daily_returns()
    n = len(rets)

    LEV = {"1배 (지수)": 1, "2배": 2, "3배": 3, "-1배 (인버스)": -1, "-2배 (곱버스)": -2}
    chosen = picks or ["1배 (지수)"]

    curves = {}
    for name in chosen:
        k = LEV[name]
        v, path = 100.0, [100.0]
        for r in rets:
            v *= (1 + k * r)
            v = max(v, 0.0)          # 전액 손실 아래로는 내려가지 않음
            path.append(v)
        curves[name] = path

    with c2:
        df = pd.DataFrame(curves, index=range(n + 1))
        df.index.name = "거래일"
        st.line_chart(df, height=330)

    # ---- 결과 표 -----------------------------------------------------
    idx_total = curves.get("1배 (지수)", [100.0, 100.0])[-1] / 100.0 - 1

    rows = []
    for name in chosen:
        k = LEV[name]
        final = curves[name][-1] / 100.0 - 1
        naive = idx_total * k
        rows.append({
            "구분": name,
            "기간 수익률": pct(final * 100),
            "단순 배율 계산": pct(naive * 100),
            "차이": pct((final - naive) * 100),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("'단순 배율 계산' = 지수 수익률 × 배율. "
               "실제와 이만큼 차이가 나는 것이 volatility drag입니다.")

    # ---- 해석 --------------------------------------------------------
    if "1배 (지수)" in chosen and len(chosen) > 1:
        worst = None
        for name in chosen:
            if name == "1배 (지수)":
                continue
            k = LEV[name]
            gap = (curves[name][-1] / 100.0 - 1) - idx_total * k
            if worst is None or gap < worst[1]:
                worst = (name, gap)
        if worst and worst[1] < -0.005:
            box(f'<span class="big brick">{worst[0]}는 단순 계산보다 '
                f'{abs(worst[1])*100:.1f}%p 더 손해를 봤습니다.</span><br>'
                '<span class="muted">이 차이가 volatility drag입니다. '
                '수수료도, 추적오차도 아닙니다. 매일 2배를 정확히 지켜서 생긴 손실입니다.</span>')
        elif worst and worst[1] > 0.005:
            box(f'<span class="big blue">{worst[0]}는 단순 계산보다 '
                f'{worst[1]*100:.1f}%p 더 벌었습니다.</span><br>'
                '<span class="muted">한 방향으로만 움직이는 추세에서는 레버리지가 유리합니다. '
                '문제는 그런 구간을 미리 알 수 없다는 점입니다.</span>')

    with st.expander("직접 확인해 볼 것"):
        st.markdown("""
- **횡보**를 고르고 배율을 1 → 2 → 3으로 올려 보세요. 손실이 배율의 몇 배로 커집니까?
- 같은 일을 **상승 추세**에서 해 보세요. 결과가 뒤집힙니까?
- **급락 후 회복**은 지수가 정확히 제자리로 돌아오게 만든 시나리오입니다.
  지수가 0%인데 2배·3배는 어디에 있습니까?
- **기간**을 10일 → 60일 → 250일로 늘려 보세요. 차이가 줄어듭니까, 벌어집니까?
- **하루 변동폭**을 키워 보세요. 변동성이 끌림을 만든다는 말의 뜻이 보입니까?
        """)

# ======================================================================
# ② 커버드콜 복권
# ======================================================================
with tab2:
    st.subheader("② 커버드콜 — 나는 복권을 파는 사람이다")
    box("콜옵션을 판다는 것은 <b>복권을 발행하는 것</b>입니다. "
        "복권 값(프리미엄)을 받아 분배금으로 나눠 줍니다. "
        "대신 당첨되는 날(주가 급등) <b>그 위로 오른 몫은 복권을 산 사람이 가져갑니다.</b> "
        "내 주머니에서 나가는 게 아니라, 벌었을 돈이 들어오지 않는 것입니다. "
        "<b class='brick'>그러면서 하락 손실은 그대로 내 몫입니다.</b>")

    c1, c2 = st.columns([1, 2])
    with c1:
        s0 = st.number_input("지금 주가 (원)", 10_000, 1_000_000, 100_000, step=5_000)
        strike_pct = st.slider("당첨 기준선(행사가) — 지금 주가보다 몇 % 위에 둘까", 0, 30, 5, step=1,
                               help="주가가 이 선을 넘으면, 넘은 만큼은 복권을 산 사람이 가져갑니다. "
                                    "내 수익은 이 선에서 멈춥니다. "
                                    "선을 낮게 둘수록 더 빨리 멈춥니다.")
        prem_pct = st.slider("복권 값(프리미엄) — 주가의 몇 %를 받을까", 0.5, 10.0, 2.0, step=0.5,
                             help="복권을 팔고 미리 받는 돈입니다. 이 돈이 분배금의 재원이 됩니다. "
                                  "당첨 기준선을 낮게 둘수록 당첨될 가능성이 커지므로, "
                                  "사는 사람이 더 비싸게 쳐줍니다.")
        shown = st.slider("한 달 뒤 주가가 이만큼 움직였다면 (%)", -40, 60, 20, step=1)

    strike = s0 * (1 + strike_pct / 100.0)
    prem = s0 * (prem_pct / 100.0)

    def payoff(end_price: float):
        plain = end_price - s0
        cc = min(end_price, strike) - s0 + prem
        return plain, cc

    xs = [s0 * (1 + p / 100.0) for p in range(-50, 71, 1)]
    curve = pd.DataFrame({
        "주식만 보유": [payoff(x)[0] for x in xs],
        "커버드콜": [payoff(x)[1] for x in xs],
    }, index=[round(x) for x in xs])
    curve.index.name = "한 달 뒤 주가 (원)"

    with c2:
        st.line_chart(curve, height=330)

    end = s0 * (1 + shown / 100.0)
    p_plain, p_cc = payoff(end)
    diff = p_cc - p_plain

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("한 달 뒤 주가", f"{end:,.0f} 원", f"{shown:+d}%")
    m2.metric("주식만 보유했다면", f"{p_plain:,.0f} 원")
    m3.metric("커버드콜이었다면", f"{p_cc:,.0f} 원")
    m4.metric("차이", f"{diff:,.0f} 원", "유리" if diff >= 0 else "불리", delta_color="off")

    if end > strike:
        lost = end - strike
        box(f'<span class="big brick">주가가 행사가({strike:,.0f}원)를 '
            f'{lost:,.0f}원 넘었습니다.</span><br>'
            f'그 {lost:,.0f}원은 전부 <b>복권 당첨자의 몫</b>입니다. '
            f'내 수익은 {p_cc:,.0f}원에서 멈춰 있습니다.')
    elif end < s0:
        box(f'<span class="big">주가가 떨어졌습니다. 손실은 {abs(p_plain):,.0f}원.</span><br>'
            f'복권 값 {prem:,.0f}원이 쿠션이 되어 {abs(p_cc):,.0f}원으로 줄었습니다. '
            '<b class="brick">다만 쿠션일 뿐, 하락을 막아주지는 않습니다.</b>')
    else:
        box(f'<span class="big blue">주가가 제자리거나 조금 올랐습니다. '
            f'커버드콜이 {diff:,.0f}원 유리합니다.</span><br>'
            '<span class="muted">커버드콜이 가장 잘 작동하는 구간입니다.</span>')

    st.markdown("---")
    st.markdown("**분배금 해부 — 받은 돈이 전부 복권 값일까**")

    d1, d2 = st.columns([1, 2])
    with d1:
        target = st.slider("약속한 연 분배율 (%)", 1, 30, 12, step=1)
        earned = st.slider("실제로 복권을 팔아 번 돈 (연 %)", 0, 30, 6, step=1)
    with d2:
        gap = max(target - earned, 0)
        comp = pd.DataFrame(
            {"연 %": [min(earned, target), gap]},
            index=["복권 값", "원금 헐기"],
        )
        st.bar_chart(comp, height=190, horizontal=True)
        st.caption("'복권 값'은 옵션 프리미엄으로 실제로 번 돈, "
                   "'원금 헐기'는 모자란 분배금을 메우려고 자산을 헐어낸 몫입니다.")

    if gap > 0:
        box(f'<span class="big brick">분배금 {target}% 중 {gap}%p는 '
            '내 원금에서 나옵니다.</span><br>'
            '통장에는 똑같이 "분배금"이라고 찍히지만, 기준가(NAV)는 그만큼 줄어듭니다. '
            '<b>분배율이 아니라 총수익(= 분배금 + 가격 변화)으로 판단해야 하는 이유입니다.</b>')
    else:
        box('<span class="big blue">번 만큼만 나눠 주고 있습니다. 원금이 녹지 않습니다.</span><br>'
            '<span class="muted">약속한 분배율을 복권 값 수입 위로 올리면 어떻게 되는지 해 보세요.</span>')

    with st.expander("직접 확인해 볼 것"):
        st.markdown("""
- 주가 슬라이더를 왼쪽 끝에서 오른쪽 끝까지 천천히 움직여 보세요. **두 선이 갈라지는 지점**은 어디입니까?
- **프리미엄**을 올려 보세요. 꺾이는 지점의 높이가 어떻게 달라집니까?
- **행사가**를 0%로, 그다음 30%로 바꿔 보세요. 분배금과 상승 여력 중 무엇이 늘고 무엇이 줄어듭니까?
- 아래 분배금 해부에서 **약속한 분배율**을 올리고 **실제로 번 돈**은 그대로 두어 보세요.
        """)

# ======================================================================
# ③ DeFi 수익 분해
# ======================================================================
with tab3:
    st.subheader("③ 연 18%는 누가 내는 돈인가")
    box("표시된 수익률(APY)은 <b>약속이 아니라 가정</b>입니다. "
        "그 수익이 ① 대출 이자 ② 거래 수수료 ③ 새로 찍어낸 토큰 중 "
        "어디에서 나오는지에 따라 실제 결과가 완전히 달라집니다.")

    c1, c2 = st.columns([1, 2])
    with c1:
        apy = st.slider("표시된 연 수익률 (%)", 1, 60, 18, step=1)
        st.markdown("**이 수익은 어디서 나오나** (합계 100%)")
        w_int = st.slider("① 대출 이자 비중 (%)", 0, 100, 20, step=5)
        w_fee = st.slider("② 거래 수수료 비중 (%)", 0, 100 - w_int, min(20, 100 - w_int), step=5)
        w_tok = 100 - w_int - w_fee
        st.markdown(f"③ 토큰 보상 비중 — <b class='brick'>{w_tok}%</b>",
                    unsafe_allow_html=True)
        tok_move = st.slider("1년 뒤 보상 토큰 가격 변화 (%)", -95, 100, -50, step=5)
        use_il = st.checkbox("유동성 공급에 따른 비영구적 손실도 반영", value=False)
        if use_il:
            price_move = st.slider("짝지은 자산의 가격 변화 (%)", -80, 300, 100, step=10)

    # 수익 분해
    r_int = apy * w_int / 100.0
    r_fee = apy * w_fee / 100.0
    r_tok_face = apy * w_tok / 100.0
    r_tok_real = r_tok_face * (1 + tok_move / 100.0)

    il = 0.0
    if use_il:
        k = 1 + price_move / 100.0
        # 정가격 공식: 2√k/(1+k) − 1
        il = (2 * math.sqrt(k) / (1 + k) - 1) * 100.0

    real = r_int + r_fee + r_tok_real + il

    with c2:
        idx = ["① 이자", "② 수수료", "③ 토큰보상"] + (["비영구적손실"] if use_il else [])
        comp = pd.DataFrame({
            "표시 기준(%p)": [r_int, r_fee, r_tok_face] + ([0.0] if use_il else []),
            "실제(%p)":      [r_int, r_fee, r_tok_real] + ([il] if use_il else []),
        }, index=idx)
        st.bar_chart(comp, height=300, horizontal=True, stack=False)
        st.caption("①과 ②는 표시와 실제가 같습니다. 차이는 ③에서만 생깁니다.")

    m1, m2, m3 = st.columns(3)
    m1.metric("표시된 수익률", f"{apy:.1f} %")
    m2.metric("실제 수익률", f"{real:+.1f} %", f"{real - apy:+.1f}%p")
    m3.metric("③ 토큰 보상이 차지하는 비중", f"{w_tok} %")

    lost = apy - real
    if real < 0:
        box(f'<span class="big brick">표시는 연 {apy}%였지만, 실제로는 {real:+.1f}%입니다.</span><br>'
            '새로 찍어낸 토큰으로 받은 수익은, 그 토큰 가격이 떨어지면 함께 사라집니다. '
            '<b>받은 것이 무엇인지 확인하지 않으면 수익률은 숫자에 불과합니다.</b>')
    elif lost > apy * 0.15:
        box(f'<span class="big brick">표시는 {apy}%였지만 실제는 {real:+.1f}%입니다. '
            f'{lost:.1f}%p가 사라졌습니다.</span><br>'
            f'이 수익의 {w_tok}%는 새로 찍어낸 토큰입니다. '
            '토큰 보상 비중이 높을수록 표시된 수익률과 실제가 벌어집니다.')
    else:
        box(f'<span class="big blue">실제 수익 {real:+.1f}%. '
            '대부분이 누군가 실제로 낸 돈에서 나왔습니다.</span><br>'
            '<span class="muted">토큰 보상 비중을 80%로 올려 보세요. 결과가 어떻게 달라집니까?</span>')

    st.markdown("---")
    st.markdown("**비교해 봅시다**")
    cmp_df = pd.DataFrame([
        {"대상": "미국 단기국채", "연 수익률": "약 4% 내외", "이 수익은 어디서 오나": "미국 정부가 내는 이자",
         "주요 위험": "거의 없음(달러 기준)"},
        {"대상": "이 DeFi 예치", "연 수익률": f"표시 {apy}% / 실제 {real:+.1f}%",
         "이 수익은 어디서 오나": f"이자 {w_int}% · 수수료 {w_fee}% · 새 토큰 {w_tok}%",
         "주요 위험": "코드 결함 · 청산 · 토큰 가격 · 운영"},
    ])
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)

    box('<span class="big">두 수익률의 차이는 보너스가 아니라, '
        '내가 떠안은 <span class="brick">위험의 가격표</span>입니다.</span>')

    with st.expander("직접 확인해 볼 것"):
        st.markdown("""
- **토큰 보상 비중**을 0%로 두고 실제 수익률을 봅니다. 그다음 80%로 올려 보세요.
- **토큰 가격 변화**를 −50%로 놓습니다. 표시된 18%는 실제로 몇 %가 됩니까?
- **비영구적 손실**을 켜고 짝지은 자산 가격을 +100%로 해 보세요. 수수료로 메워집니까?
- 표시 수익률을 60%까지 올려 보세요. 그런 수익률이 무엇으로 지급될지 짐작이 갑니까?
        """)

st.markdown("---")
st.caption("ETF_Coin · 가계자산 투자설계 11·12주차 · 모든 계산은 이 화면 안에서만 이루어집니다.")
