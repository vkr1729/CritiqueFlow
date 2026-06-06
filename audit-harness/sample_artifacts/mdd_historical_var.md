# Model Development Document (MDD)
## Historical Simulation Value-at-Risk (HS-VaR) Model

**Model ID:** MR-VAR-HS-3.2  
**Effective Date:** November 2025  
**Version:** 3.2  
**Owner:** Market Risk Analytics and Quantitative Research Group  
**Target Portfolio:** Global Trading Book (Equities, Fixed Income, FX, and Commodities)  
**Regulatory Framework:** Basel III / CRD IV / FRTB (Fundamental Review of the Trading Book)

---

## 1. Executive Summary & Scope
The Model Development Document (MDD) defines the methodology, mathematical foundations, data ingestion pipelines, assumptions, and limitations of the Bank’s Historical Simulation Value-at-Risk (HS-VaR) pricing engine. 

The HS-VaR model is the primary regulatory capital model used to compute the Market Risk Capital Charge for the Global Trading Book. It measures the potential loss in portfolio value over a 1-day holding period at a 99% confidence level, using a 250-day rolling historical window of daily market risk factor movements. 

Additionally, this document specifies the extensions for **Stressed Value-at-Risk (sVaR)** (calculated using a continuous 12-month period of significant financial stress) and the transitioning framework for **Expected Shortfall (ES)** under the Basel III FRTB standards.

---

## 2. Methodological Framework
The HS-VaR model uses a non-parametric Historical Simulation approach. The underlying principle is that the historical distribution of risk factor changes over a preceding observation period (250 business days) is a representative estimator of the future joint distribution of risk factor changes over the next business day.

### 2.1 Risk Factor Identification
The model maps the bank's trading portfolio to $M = 14,500$ distinct risk factors, categorized into four asset classes:
1.  **Interest Rates & Credit Spreads:** Yield curves (Libor/SOFR tenors), inflation swaps, sovereign spreads, corporate credit spreads (CDS tenors).
2.  **Equities:** Individual stock prices, equity indices, implied volatilities (smile/skew surfaces).
3.  **Foreign Exchange (FX):** Spot FX rates, FX forward points, FX implied volatilities.
4.  **Commodities:** Spot/Futures prices (Crude Oil, Natural Gas, Gold, Copper), commodity implied volatilities.

### 2.2 Return Calculation Schemes
To simulate future market moves, daily historical returns are calculated for each risk factor $i$ on each business day $t$ within the 250-day window:
*   **Logarithmic Returns:** Used for Equities, FX, and Commodities to ensure price non-negativity:
    $$R_{i,t} = \ln\left(\frac{S_{i,t}}{S_{i,t-1}}\right)$$
*   **Absolute Differences:** Used for interest rates, bond yields, and credit spreads to handle near-zero or negative rates:
    $$\Delta Y_{i,t} = Y_{i,t} - Y_{i,t-1}$$
*   **Relative Returns:** Used for implied volatilities:
    $$R_{i,t}^{vol} = \frac{\sigma_{i,t} - \sigma_{i,t-1}}{\sigma_{i,t-1}}$$

### 2.3 Valuation & P&L Reperformance
For each historical scenario $t \in [1, 250]$, the risk factor changes are applied to current market levels to generate "scenarized" risk factor inputs. The portfolio is then valued under each scenario:
1.  **Full Revaluation (Linear and Standard Non-Linear Instruments):** For equities, foreign exchange, bonds, and vanilla options, the pricing models recompute the present value ($PV$) of each trade. The scenario P&L ($\Delta \Pi_t$) is computed as:
    $$\Delta \Pi_t = \sum_{j=1}^{N} \left[ PV_j(S_t) - PV_j(S_0) \right]$$
    Where $S_t$ represents the vector of risk factors under scenario $t$, and $S_0$ represents current market levels.
2.  **Delta-Gamma Approximation (Exotic Options & High-Dimensional Derivatives):** To reduce computational latency, complex exotic derivatives (e.g., barrier options, equity autocalc, multi-asset baskets) are valued using a Taylor-series approximation up to the second order:
    $$\Delta PV_j \approx \sum_{k} \Delta_{j,k} \Delta S_{k,t} + \frac{1}{2} \sum_{k} \sum_{l} \Gamma_{j,k,l} \Delta S_{k,t} \Delta S_{l,t} + \theta_j \Delta t$$
    Where $\Delta_{j,k}$ is the first derivative (Delta), $\Gamma_{j,k,l}$ is the second derivative (Gamma), and $\theta_j$ is the time decay (Theta).

### 2.4 VaR & sVaR Calculation
The 250 scenario P&Ls are sorted in ascending order:
$$\Delta \Pi_{(1)} \le \Delta \Pi_{(2)} \le \dots \le \Delta \Pi_{(250)}$$

*   **1-Day 99% VaR:** The VaR is defined as the 2.5th worst loss, obtained via linear interpolation between the 2nd and 3rd ordered observations:
    $$VaR_{0.99} = - \left( 0.5 \cdot \Delta \Pi_{(2)} + 0.5 \cdot \Delta \Pi_{(3)} \right)$$
*   **Stressed VaR (sVaR):** Computed using the same mathematical framework but over a fixed 250-day window representing a period of extreme stress. The chosen historical period is the Lehman Crisis: **July 2, 2008, to June 30, 2009**.

### 2.5 Expected Shortfall (ES)
To conform with the Basel III FRTB rules, the engine computes the 97.5% Expected Shortfall (ES). Expected Shortfall calculates the average of the losses exceeding the 97.5% VaR threshold:
$$ES_{0.975} = -\frac{1}{6} \sum_{k=1}^{6} \Delta \Pi_{(k)}$$
Where the 6 worst losses out of the 250 scenarios represent the tail beyond the 97.5% confidence limit.

---

## 3. Core Model Assumptions
The conceptual soundness of the HS-VaR model relies on several key quantitative assumptions. Violation of these assumptions represents a material source of model risk:

1.  **Stationarity of Joint Distributions:** The joint distribution of risk factor returns over the next business day is assumed identical to the empirical distribution observed over the past 250 days. This assumes that volatility levels, correlations, and skewness are stationary.
2.  **Static Portfolio Assumption (Holding Period):** The 1-day holding period assumes that the portfolio composition remains constant over the 24-hour horizon. It assumes no intra-day trading, hedging, or position unwinding takes place.
3.  **Linear Risk Factor Mapping:** For complex products, it is assumed that mapping risk exposures to liquid proxy risk factors does not introduce unhedged basis risk.
4.  **Delta-Gamma Sufficiency:** For derivatives priced via approximation, third-order and higher-order terms (e.g., speed, cross-gamma, vanna, volga) are assumed to be immaterial.

---

## 4. Model Limitations & Vulnerabilities
Developers have identified the following structural limitations of the HS-VaR model:

1.  **Ghost Features / Age-of-Data Effect:** Because the 250-day window is equally weighted, a severe market shock (e.g., a massive 500-bp rate jump) enters the window with a weight of $1/250$ (0.4%) and remains there for exactly 250 days. On day 251, the shock drops out of the window completely, causing an artificial and abrupt drop in VaR, even if market conditions remain highly volatile.
2.  **Tail Insensitivity:** VaR only identifies the threshold of loss at the 99% level; it provides no information on the distribution or magnitude of losses in the 1% tail (e.g., whether the maximum loss is $10 million or $100 million).
3.  **Underestimation of Sudden Volatility Spikes:** If the market enters a regime of high volatility after a long period of low volatility, the historical simulation will significantly underestimate the risk because 99% of the scenarios in the window reflect the low-volatility regime.
4.  **Illiquid Risk Factor Mapping (Basis Risk):** Illiquid risk factors (e.g., exotic credit spreads or emerging market currency pairs) that do not have daily market feeds are mapped to liquid index proxies. This assumes a constant basis between the exotic asset and the proxy, which routinely breaks down during market crises.

---

## 5. Model Performance Monitoring & Controls
To ensure the model remains fit for purpose, the following control framework is established:

### 5.1 Backtesting Protocol
Daily backtesting compares the 1-day 99% VaR to the actual trading P&L (Hypothetical P&L and Actual P&L):
*   **Hypothetical P&L (H-P&L):** The P&L generated by applying the actual daily market risk factor movements to the static portfolio at the end of the previous day (no fee, commission, or intraday trading income included).
*   **Actual P&L (A-P&L):** The actual P&L recorded by product control, including intraday trading fees and commissions.

A **Backtesting Exception** occurs if the daily loss exceeds the VaR computed the previous day:
$$\text{Exception} = 1 \quad \text{if} \quad \Delta \Pi_t < -VaR_{t-1}$$

Under Basel guidelines, exceptions are tracked over a rolling 250-day window to determine the regulatory zone:
*   **Green Zone (0 to 4 exceptions):** Multiplier ($mc$) remains at 3.0.
*   **Amber Zone (5 to 9 exceptions):** Multiplier increases incrementally from 3.4 to 3.8.
*   **Red Zone (10+ exceptions):** Multiplier is set to 4.0, and the model authority may be revoked.

### 5.2 Data Ingestion & Quality Control
*   **Bloomberg/Reuters End-of-Day (EOD) Feeds:** Raw market data is ingested daily at 18:30 EST.
*   **Stale Data Detection:** If a risk factor price does not change for 3 consecutive days, the system logs a "stale data warning."
*   **Outlier Cap:** Daily risk factor returns exceeding $\pm 4$ standard deviations of the historical series are flagged for manual verification. If verified as correct, they are processed; if flagged as erroneous, they are replaced using linear interpolation of adjacent dates.
