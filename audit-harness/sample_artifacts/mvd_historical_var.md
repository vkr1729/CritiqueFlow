# Independent Model Validation Report (MVR)
## Historical Simulation Value-at-Risk (HS-VaR) Model

**Validation Report ID:** MRM-VAL-VAR-2025-04  
**Validation Date:** December 2025  
**Validator:** Model Risk Management (MRM) Group - Market Risk Team  
**Model Under Review:** Historical Simulation Value-at-Risk (HS-VaR) Engine (Version 3.2)  
**Model ID:** MR-VAR-HS-3.2  
**Validation Status:** Conditionally Approved (subject to remediation of Findings)

---

## 1. Executive Summary & Validation Opinion
Model Risk Management (MRM) has conducted an independent validation of the Historical Simulation Value-at-Risk (HS-VaR) Engine (v3.2). The model is designed to calculate regulatory capital under Basel III and internal risk limits for the Global Trading Book.

### 1.1 Overall Validation Opinion
MRM grants **Conditional Approval** for the HS-VaR v3.2 model. The model is conceptually sound and provides reasonable capital estimates under normal market conditions. However, the model has material vulnerabilities during market stress and regime shifts. 

We have identified **four critical findings**—two of which are rated **High Severity** and require immediate remediation before full approval can be granted. The trading desks are permitted to continue using the model for capital calculations, provided that the capital multipliers are adjusted to account for these findings.

| Finding ID | Description | Severity | Remediation Deadline | Status |
|------------|-------------|----------|----------------------|--------|
| **VF-01**  | Inaccurate pricing of exotic equity barrier options via Delta-Gamma approximation | **High** | Q1 2026 | Open |
| **VF-02**  | Proxy mapping basis risk in the Emerging Markets credit spread portfolio | **High** | Q2 2026 | Open |
| **VF-03**  | "Ghost Feature" and slow adaptation of equal-weighted historical simulation | **Medium** | Q3 2026 | Open |
| **VF-04**  | Outdated Stressed VaR historical window calibration | **Medium** | Q2 2026 | Open |

---

## 2. Conceptual Soundness & Assumption Validation
MRM evaluated the core assumptions documented in the Model Development Document (MDD). 

### 2.1 Evaluation of Equal Weighting Assumption
The model assumes that all 250 historical scenarios in the rolling window are equally likely to occur, each carrying a weight of $1/250$ ($0.4\%$). 
*   **MRM Challenge:** This assumption is conceptually flawed. During periods of rising market volatility (e.g., Q3 2025 interest rate spikes), the equal-weighted approach significantly understates the current risk because it treats a shock that occurred 240 days ago with the same importance as a shock that occurred yesterday. 
*   **Outcome:** This causes a lag in model response, leading to backtesting breaches during the onset of market crises. On the other hand, the model suffers from the "ghost feature" where a major shock suddenly drops out of the window after 250 days, causing VaR to fall abruptly by up to 15% without any corresponding reduction in portfolio risk.

### 2.2 Validation of Delta-Gamma Approximation vs. Full Revaluation
The development team utilizes a Delta-Gamma Taylor-series approximation for exotic options to save computing power.
*   **MRM Challenge:** For exotic derivatives with highly non-linear profiles—such as equity barrier options (Knock-ins/Knock-outs) and autocallables—the first- and second-order derivatives (Delta and Gamma) do not capture the risk near the barrier. As the spot price approaches the barrier, Gamma changes rapidly (exhibiting high "Speed" or third-order derivatives), and cross-gamma terms become highly material.
*   **Quantitative Test:** MRM priced a sub-portfolio of EUR Equity Autocallable Notes using both the model's Delta-Gamma approximation and an independent full-revaluation Monte Carlo engine under a stress scenario of a $-15\%$ equity drop. 
    *   **Model Price Change (Delta-Gamma):** Estimated loss of **$8.2 million**.
    *   **Independent Price Change (Full Reval):** Realized loss of **$11.4 million**.
    *   **Error:** The Delta-Gamma approximation underestimated the portfolio loss by **28.0%**.

### 2.3 Proxy Mapping and Basis Risk Assessment
For illiquid risk factors, the model maps exposures to liquid benchmarks.
*   **MRM Challenge:** The Emerging Markets credit spread portfolio maps exotic Turkish and Brazilian corporate debt spreads to the liquid EM Sovereign Index (EMBI). 
*   **Outcome:** During idiosyncratic country-level stress events, the corporate spreads widened by over 300 bps while the EMBI sovereign index widened by only 45 bps. Because the model assumed a fixed relationship, the VaR engine failed to capture the €3.4 million basis loss.

---

## 3. Quantitative Testing & Outcome Analysis

### 3.1 Backtesting Verification
MRM reperformed the historical backtesting using the trading desk's portfolio from November 2024 to November 2025 (250 business days). 

```
                                  Backtesting Results (1-Year Rolling)
           5.0M |                                                    
                |                                      * [Breach 3]
           2.5M |                   * [Breach 1]      
                |                                  * [Breach 2]      
 P&L / VaR      |----------------------------------------------------  <-- VaR Threshold
                |                                                    
          -2.5M |                                                    
                |   *                                                
          -5.0M |____________________________________________________
                                    Time (Days 1 - 250)
```

During this period:
*   The model recorded **6 backtesting exceptions** against the Hypothetical P&L.
*   Under Basel III rules, this places the model in the **Amber Zone** (where 5 to 9 exceptions are observed).
*   **Statistical Analysis:** 
    *   **Kupiec Proportion of Overjections (POF) Test:** The null hypothesis that the exception rate is exactly 1% was rejected at the 95% confidence level (p-value = 0.038). This indicates that the model systematically underestimates tail risk.
    *   **Christoffersen Interval Forecast Test:** The test detected clustering of breaches (Breaches 2 and 3 occurred within 3 days of each other). The null hypothesis of independence was rejected (p-value = 0.012), indicating the model fails to adjust volatility estimates quickly enough during stress.

### 3.2 Benchmark Comparison
MRM compared the 1-Day 99% HS-VaR against an independent **Filtered Historical Simulation (FHS)** model incorporating a GARCH(1,1) volatility filter.
*   **Average HS-VaR (v3.2):** **$3.1 million**
*   **Average FHS-VaR (Independent):** **$4.4 million**
During high-volatility regimes, the independent model adjusted immediately, outputting a VaR up to **42% higher** than the production model, demonstrating that the production model is under-capitalized during stress.

---

## 4. Severity Assessment & Remediation Actions

### VF-01: Exotic Option Valuation (Severity: HIGH)
*   **Root Cause:** Delta-Gamma approximation fails to capture high-order non-linearities and barrier risk.
*   **Impact:** Underestimation of potential trading losses for structured notes by up to $3.2 million under stress.
*   **Condition for Remediation:** The quantitative development team must retire the Delta-Gamma approximation for all option contracts containing barrier or path-dependent triggers. These contracts must be migrated to a full revaluation scheme in the daily VaR calculation by **March 31, 2026**.

### VF-02: Proxy Mapping Basis Risk (Severity: HIGH)
*   **Root Cause:** Inadequate mapping of illiquid EM credit spreads to sovereign indices without mapping error adjustments.
*   **Impact:** Missing idiosyncratic credit shocks, underestimating VaR for the EM desk by up to 25%.
*   **Condition for Remediation:** Implement a "Risk Not In VaR" (RNIV) capital add-on framework. The model must add a historical basis spread volatility charge to the VaR output for any position where the proxy correlation falls below 0.70. Deadline: **June 30, 2026**.

### VF-03: Ghost Feature of Equal Weighting (Severity: MEDIUM)
*   **Root Cause:** Equal-weighted 250-day scenario window.
*   **Impact:** Abrupt drops in VaR when volatile days leave the window; slow adaptation to new volatility regimes.
*   **Condition for Remediation:** The developers must test and document a transition plan to either a Volatility-Weighted Historical Simulation (HW-VaR) or an Expected Shortfall engine with decaying weights ($\lambda = 0.975$). Deadline: **September 30, 2026**.

### VF-04: Outdated Stressed VaR Window (Severity: MEDIUM)
*   **Root Cause:** Stressed VaR period has remained fixed to the 2008 Lehman crisis.
*   **Impact:** Ignores recent severe market stress events (such as the 2020 COVID liquidity crunch or the 2022-2023 interest rate hiking cycle) which are more relevant to the bank's current portfolio profile.
*   **Condition for Remediation:** Perform an annual review of the 12-month stress period. The quant team must compare Lehman 2008 against COVID 2020 and 2022 rate spikes to determine the most conservative period for sVaR calculations. Deadline: **June 30, 2026**.
