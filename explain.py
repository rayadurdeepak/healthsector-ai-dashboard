"""
Rule-based "AI Explanation" -- turns a prediction row's numbers into a
short, plain-English reason. Not a language model call (no extra cost/
dependency); just templated logic over columns we already compute. Good
enough to answer "why is it saying this" at a glance on the dashboard.
"""

import pandas as pd


def explain_row(row: pd.Series) -> str:
    bits = []

    conf = row.get("Prediction Confidence (%)")
    if pd.notna(conf):
        if conf >= 90:
            bits.append(f"Models strongly agree with each other ({conf:.0f}% confidence)")
        elif conf >= 75:
            bits.append(f"Models reasonably agree ({conf:.0f}% confidence)")
        else:
            bits.append(f"Models disagree more than usual ({conf:.0f}% confidence -- treat with extra caution)")

    rsi = row.get("RSI")
    if pd.notna(rsi):
        if rsi < 30:
            bits.append(f"RSI at {rsi:.0f} suggests oversold (possible bounce)")
        elif rsi > 70:
            bits.append(f"RSI at {rsi:.0f} suggests overbought (possible pullback)")

    macd, macd_sig = row.get("MACD"), row.get("MACD Signal")
    if pd.notna(macd) and pd.notna(macd_sig):
        bits.append("MACD is bullish (above signal line)" if macd > macd_sig
                     else "MACD is bearish (below signal line)")

    adx = row.get("ADX")
    if pd.notna(adx) and adx >= 25:
        bits.append(f"ADX at {adx:.0f} shows a strong trend (in either direction)")

    sentiment = row.get("Sentiment")
    strategy = row.get("Strategy Signal") or row.get("Strategy")
    if pd.notna(sentiment) and sentiment not in ("Neutral", None):
        news_bit = f"Recent news sentiment is {sentiment}"
        if pd.notna(strategy) and strategy not in ("Normal", None):
            news_bit += f" ({strategy})"
        bits.append(news_bit)

    ret = row.get("Expected Return (%)")
    if pd.notna(ret):
        direction = "gain" if ret >= 0 else "drop"
        bits.append(f"Ensemble expects a {abs(ret):.1f}% {direction} over the next month")

    dist_high = row.get("Distance From 52W High (%)")
    if pd.notna(dist_high):
        if dist_high < 5:
            bits.append("Trading near its 52-week high")
        elif dist_high > 40:
            bits.append("Trading well below its 52-week high")

    agreement = row.get("Signal Agreement")
    if agreement == "Disagreement":
        bits.append("NOTE: the return-based signal and the composite AI score disagree -- worth a manual look")

    if not bits:
        return "Not enough signal to explain confidently -- treat as neutral."

    return ". ".join(bits) + "."
