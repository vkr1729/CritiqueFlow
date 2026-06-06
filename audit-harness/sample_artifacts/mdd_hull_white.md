# Model Development Document (MDD)
## Hull-White One-Factor Short Rate Model (HW1F)

**Model Identifier:** HW1F-IR-01  
**Date:** March 2025  
**Developer:** Quantitative Research Group  
**Target Asset Class:** Interest Rate Derivatives (Bermudan Swaptions, Callable Range Accruals)

---

### 1. Mathematical Framework
The model represents the dynamics of the short rate $r_t$ under the risk-neutral measure using the Hull-White one-factor process:
$$dr_t = (\theta(t) - a r_t) dt + \sigma dW_t$$

Where:
*   $\theta(t)$ is a time-varying function calibrated to fit the initial term structure of interest rates exactly.
*   $a$ is the mean reversion parameter, assumed constant at $a = 0.03$.
*   $\sigma$ is the instantaneous volatility parameter, assumed constant at $\sigma = 0.015$.
*   $W_t$ is a standard one-dimensional Brownian motion.

### 2. Core Model Assumptions
1.  **Constant Parameters:** Both mean reversion $a$ and volatility $\sigma$ are treated as time-invariant constants to simplify trinomial tree construction and speed up calibration.
2.  **Single Factor:** Interest rate moves across all tenors are perfectly correlated (driven by a single Brownian motion $W_t$).
3.  **Normal Distribution:** The short rate $r_t$ is normally distributed, meaning there is a mathematically non-zero probability of negative interest rates.
4.  **Yield Curve Interpolation:** The initial yield curve is constructed using cubic spline interpolation of swap rates, ignoring potential negative forward rate occurrences.

### 3. Calibration Methodology
Calibration is performed daily using At-The-Money (ATM) European Swaption implied volatility grids. The calibration engine runs a least-squares minimization to fit the model prices of ATM European swaptions to the market-implied Black-76 prices:
$$\min_{a, \sigma} \sum_{i=1}^{N} (P_{HW}^{i}(a, \sigma) - P_{Black}^{i})^2$$

*Note: For the calibration, the mean reversion $a$ is locked at $0.03$, and only $\sigma$ is optimized to match the swaption prices closest to the target maturity.*

### 4. Limits and Boundaries
*   The model assumes interest rates remain within the range of $-1.5\%$ to $+10\%$.
*   If calibration fails, the engine uses the parameters from the previous business day.
