# Periodic Audit Review (PAR)
## Historical Simulation Value-at-Risk (HS-VaR) Engine

**Audit Report ID:** AUD-MR-VAR-2025-Q4  
**Audit Period:** Q4 2025  
**Audit Conducted By:** Internal Audit - Model Risk & Market Risk Audit Group  
**Lead Auditor:** Senior Model Risk Auditor  
**Date of Report:** January 2026

---

## 1. Audit Objective & Executive Summary
Internal Audit has completed its periodic review of the Bank's Historical Simulation Value-at-Risk (HS-VaR) Model (Model ID: MR-VAR-HS-3.2) and its associated operational workflows for Q4 2025. 

The audit focused on evaluating the model's operational performance, backtesting validity, data quality controls, compliance with Basel III market risk capital rules, and the desk's adherence to model governance policies.

### 1.1 Audit Assessment Rating: UNSATISFACTORY
Internal Audit has rated the operational controls and performance of the HS-VaR model as **Unsatisfactory**. 

During the audit period, the model experienced a high frequency of backtesting exceptions, placing the model in the **Basel Amber Zone** and increasing the regulatory capital multiplier. Furthermore, we identified **two significant policy violations** where the front office manually bypassed model parameters to avoid VaR spikes, and one severe **data quality issue** that went undetected by daily operational checks.

---

## 2. Key Audit Findings & Detailed Issues

### Finding 1: Unapproved Manual Override of Volatility Proxies (High Risk)
*   **Audit Observation:** On November 11 and 12, 2025, during a period of extreme volatility in Emerging Markets sovereign debt, the FX trading desk manually disabled the volatility scaling factor for Turkish Lira (TRY) and Brazilian Real (BRL) currency pairs within the risk mapping table.
*   **Root Cause Analysis:** If the scaling factor had remained active, the simulated TRY/BRL exchange rate fluctuations would have triggered a VaR limit breach for the FX desk, forcing them to reduce their exposures. By disabling the volatility scaling factor, the desk kept their reported VaR artificially low.
*   **Regulatory & Control Impact:** This action constitutes an unauthorized model change and a breach of model governance protocols (violating SR 11-7 model change control guidelines). It resulted in under-reporting the bank's 99% VaR by **$1.8 million** over a 48-hour period. Product Control was not notified of this override.

### Finding 2: Out-of-Date Stressed VaR (sVaR) Stress Period (Medium Risk)
*   **Audit Observation:** The historical stress window used to calculate Stressed VaR (sVaR) has remained fixed as the Lehman Crisis period (July 2008 to June 2009) since 2018. 
*   **Root Cause Analysis:** The quantitative research group has failed to execute the required annual review to verify if the 2008 Lehman period remains the most conservative stress window for the bank's current portfolio.
*   **Impact:** Due to significant portfolio shifts toward interest rate options and inflation swaps, the 2022-2023 inflation-driven rate hike cycle represents a more severe stress period. Re-running the sVaR engine using the 2022-2023 interest rate crisis showed a capital shortfall of **$4.1 million** compared to the Lehman calculations. The bank is currently under-capitalized for interest rate risk.

### Finding 3: Operational Failure in Daily Data Quality Checks (Medium Risk)
*   **Audit Observation:** Between October 14 and October 18, 2025 (5 consecutive business days), the Bloomberg data feed for the US Treasury 10-Year yield index failed to deliver daily volatility levels due to a schema change at the data provider.
*   **Root Cause Analysis:** The daily data quality check engine failed to trigger an alert. Instead, the system automatically fell back to a "flat-line" data replacement logic, inserting a change of $0.00$ bps for all 5 days.
*   **Impact:** The flat-line substitution artificially suppressed the historical volatility of the US interest rate curve. This caused the 99% VaR for the Fixed Income desk to drop by **12%** on October 18, 2025, during a week when the market was actually highly volatile. Risk management made limit-allocation decisions based on these suppressed VaR numbers.

---

## 3. Backtesting Performance & Basel Capital Impact
Internal Audit reperformed the regulatory backtesting calculations for the 250-day window ending December 31, 2025. 

### 3.1 Backtesting Breaches Log (Q4 2025)
Four of the six rolling 12-month breaches occurred during the Q4 audit period:

1.  **October 10, 2025:** 
    *   *Hypothetical Loss:* **$3.8 million** vs. *VaR:* **$2.9 million** (Breach of $0.9 million).
    *   *Desks Involved:* Fixed Income Desk.
    *   *Trigger:* Unanticipated 25-bp rate increase by the European Central Bank.
2.  **November 12, 2025:** 
    *   *Hypothetical Loss:* **$4.2 million** vs. *VaR:* **$3.1 million** (Breach of $1.1 million).
    *   *Desks Involved:* FX Desk.
    *   *Trigger:* Turkish Lira sudden currency devaluation.
3.  **December 18, 2025:** 
    *   *Hypothetical Loss:* **$3.6 million** vs. *VaR:* **$2.8 million** (Breach of $0.8 million).
    *   *Desks Involved:* Equity Derivatives Desk.
    *   *Trigger:* Severe sell-off in European automotive sector.
4.  **December 22, 2025:**
    *   *Hypothetical Loss:* **$3.9 million** vs. *VaR:* **$2.9 million** (Breach of $1.0 million).
    *   *Desks Involved:* Equity Derivatives Desk.
    *   *Trigger:* High-frequency correlation breakdowns in index components.

### 3.2 Basel Capital Penalty
With **6 total breaches** over the rolling year, the bank is officially in the **Basel Amber Zone**.
*   The regulatory capital multiplier ($m_c$) has been increased from **3.00 to 3.50**.
*   This increase represents an immediate addition of **$18.5 million** to the bank's required Market Risk regulatory capital reserve.

---

## 4. Required Audit Remediation Actions (MRA)

1.  **MRA 1: Access Controls & Override Logs (High Risk):** Implement hard database constraints to prevent manual modification of volatility proxies or risk mapping tables. Any emergency override must require dual-authorization (Trading Head and Head of Market Risk) and must be automatically logged. Deadline: **February 28, 2026**.
2.  **MRA 2: Stressed VaR Window Recalibration (Medium Risk):** Re-calibrate the sVaR stress period. The Market Risk Quant team must implement an automated script that evaluates the portfolio under different historical 12-month stress windows (2008 Lehman, 2020 COVID, 2022 Rates) on a quarterly basis. Deadline: **April 30, 2026**.
3.  **MRA 3: Data Quality Alert Logic (Medium Risk):** Re-engineer the data validation checks in the ETL pipeline. Flat-line data entries for critical risk factors must trigger a high-priority alert and prevent the VaR calculation from finalizing until a manual sign-off is completed. Deadline: **March 31, 2026**.
