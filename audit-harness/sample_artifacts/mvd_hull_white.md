# Independent Model Validation Report (MVR)

## Hull-White One-Factor Short Rate Model (HW1F-IR-01)

**Validation Date:** May 2025  
**Validator:** Model Risk Management (MRM) Group  
**Status:** Conditionally Approved (subject to remediation of Findings)

---

### 1. Executive Summary

This report presents the independent validation of the Hull-White One-Factor (HW1F) pricing library. The model is intended for pricing and risk-managing Bermudan Swaptions and Callable Range Accruals in the EUR and USD portfolios. The validation team concluded that the mathematical formulation is standard and generally sound, but identifies significant vulnerabilities regarding calibration stability and single-factor assumptions.

### 2. Validation Scope & Approach

The validation scope includes:

* Reviewing the mathematical foundation and conceptual soundness.
* Independent implementation of the pricing formulas for ATM European Swaptions to verify implementation accuracy.
* Sensitivity analysis of the model prices to changes in input parameters ($a$ and $\sigma$).

### 3. Conceptual Soundness & Assumptions Assessment

* **Single-Factor Limitation:** The single-factor formulation assumes perfect correlation of all tenors. While acceptable for simple European options, this assumption is inadequate for range accruals that pay coupons based on the spread between short-term (e.g., 3M Euribor) and long-term (e.g., 10Y Swap) rates.
* **Constant Mean Reversion:** The development team has locked the mean reversion parameter at $a = 0.03$. The validation team reviewed this and accepted it because it stabilizes the calibration of the volatility parameter $\sigma$.
* **Negative Rates:** The model's normal distribution allows negative rates. The validator notes that negative rates are currently observed in the Eurozone, so this is a realistic feature. No further tests were conducted for negative rate boundaries.

### 4. Quantitative Testing Results

* **Benchmarking:** Independent validation code matched the development team's European swaption prices within $0.05$ basis points.
* **Sensitivity Analysis:**
  * A $+10\%$ increase in $\sigma$ results in an average $+8.5\%$ increase in Bermudan swaption value.
  * The model prices are relatively insensitive to the mean reversion parameter $a$ within the range $[0.01, 0.05]$.

### 5. Validation Finding (VF-01)

* **Severity:** Medium
* **Description:** The calibration engine fails to converge when the volatility surface exhibits extreme skew or smile (e.g., during period of interest rate stress).
* **Remediation Required:** The development team must implement a backup calibration routine that falls back to a historical average volatility if the optimization engine fails to converge within 100 iterations.
