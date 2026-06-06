# Periodic Audit Review (PAR)
## Hull-White One-Factor Short Rate Model (HW1F-IR-01)

**Audit Period:** Q4 2025  
**Reviewer:** Internal Audit - Model Risk Team  
**Date:** January 2026

---

### 1. Performance Summary
During Q4 2025, the interest rate trading desk experienced significant market volatility, with the Euro short rate entering deeply negative territory (reaching $-0.45\%$). This period of stress revealed several severe vulnerabilities in the HW1F-IR-01 pricing system.

### 2. Key Audit Findings & Breaches

#### Finding 1: Calibration Failures & Static Parameter Fallback
During October and November 2025, the calibration engine failed to converge on **14 separate trading days** due to the extreme steepness of the Euro yield curve.
*   **Audit Observation:** In all 14 instances, the system automatically fell back to the previous day's parameters without alerting the risk management department.
*   **Impact:** The model priced Bermudan Swaptions worth €450 million using stale parameters for up to 5 consecutive days, leading to a calculated misvaluation of €1.8 million in the desk's book.

#### Finding 2: Float-Point Errors (NaNs) under Negative Rates
On December 18, 2025, the EUR short rate dropped below $-0.40\%$. The callable range accrual solver (which uses the HW1F trinomial tree) threw floating-point execution errors (`NaN` values) in production.
*   **Audit Observation:** The trading desk bypassed the system crash by manually setting a floor of $+0.01\%$ (1 bp) in the database for the short rate calculation.
*   **Impact:** Bypassing the model logic caused the range accrual contracts to pay coupons as if interest rates were positive, resulting in an overpayment of €2.1 million to counterparties. This manual override was not documented, nor was it approved by the Model Risk Committee (violating SR 11-7 model change control guidelines).

#### Finding 3: Volatility Smile & Skew Mispricing
The one-factor model assumes constant volatility $\sigma$, which does not capture the volatility smile/skew.
*   **Audit Observation:** Benchmarking against a multi-factor SABR model showed that the HW1F model mispriced out-of-the-money (OTM) options by up to **$22\%$** during peak volatility.
*   **Impact:** The desk's portfolio is currently over-hedged on the short end and under-hedged on the long end, leaving the bank exposed to yield curve twists.
