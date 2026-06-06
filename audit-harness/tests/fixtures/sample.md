# Sample Audit Model Document

## Model Overview

This document describes the **Valuation Risk Model v2.3** used for pricing exotic equity derivatives.

## Methodology

The model employs a **Heston stochastic volatility** framework with the following key parameters:

- Initial volatility (v0): 0.04
- Long-run variance (theta): 0.04
- Mean reversion rate (kappa): 2.0
- Volatility of volatility (xi): 0.3
- Correlation (rho): -0.7

## Risk Considerations

The model has been validated against SR 11-7 guidelines. Key findings include:

1. Calibration stability is adequate within normal market conditions
2. Stress testing reveals sensitivity to correlation parameter
3. Backtesting results show 97.5% pass rate at 99% VaR confidence level

## Conclusion

The model is deemed fit for purpose subject to the recommended monitoring frequency of quarterly re-validation.
