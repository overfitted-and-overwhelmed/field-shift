# AGRIscora

**Team name:** Overfitted and Overwhelmed
**Project title:** AGRIscora
**NASA Space Apps Challenge 2026:** Field Shift: Adapting Farms with NASA Data
**Live Demo:** [https://field-shift-beta.vercel.app](https://field-shift-beta.vercel.app)

## Overview
**AGRIscora** was created during the **Hackatron** for the **NASA Space Apps Challenge 2026** (*Field Shift: Adapting Farms with NASA Data*). It is an intelligent crop rotation scoring and decision-support tool designed to help farmers adapt their fields to a changing climate by evaluating and ranking multi-year crop rotations across water demand, climate risk, nitrogen requirements, and soil health.

## What We Built
- **Crop Scorer:** Models multi-year rotation performance, calculating irrigation needs (FAO-56 water balance), climate risk (heat and frost stress from temperature bounds), nitrogen dynamics, and erosion risk (bare soil days).
- **Rotation Explorer:** Compiles multi-year rotation metrics, seasonal yields, and monthly water/risk breakdowns with complete data provenance.
- **Farmer Advisor & MCP Server:** An interactive decision-support interface and Model Context Protocol (MCP) server that explains rotation trade-offs and allows farmers to re-rank candidate rotations based on their specific priorities (e.g., water savings vs. soil health).

## NASA Data & Resources
- **NASA POWER (Prediction Of Worldwide Energy Resources):** Daily meteorological data (precipitation, $T_{min}$, $T_{max}$, $T_{mean}$, solar radiation, and relative humidity) from 1991 to 2025.
- **Climate & Water Stress Modeling:** NASA POWER daily weather time-series are used to compute reference evapotranspiration ($ET_0$), historical water deficits, daily crop water demand ($ET_c$), and growth-stage heat/cold stress probabilities.

## External Data & Resources
- **USDA NRCS & NCSS (SSURGO, NCSS Lab Data Mart, Termination Guidelines):** Soil profile horizon data (available water capacity, organic matter, texture, bulk density, hydrologic group) to parameterize root-zone water storage, along with NRCS cover crop termination rules.
- **ISRIC SoilGrids:** Gridded soil properties across standard depths (0–200 cm) used to cross-validate SSURGO soil characteristics.
- **USDA NASS & ERS (CDL, Quick Stats, AH-628, AH-697):** Cropland Data Layer (CropScape) for field crop history (2008–2025), Quick Stats API for county-level baseline yields and prices, Handbook 628 for Kansas planting/harvesting dates, and ERS AH-697 for bushel weight and moisture conversions.
- **FAO (FAO-56 & Ecocrop):** FAO-56 Penman-Monteith method, growth stage lengths (Table 11), crop coefficients $K_c$ (Table 12), rooting depths $Z_r$ and depletion fractions $p$ (Table 22) for water balance modeling, and Ecocrop temperature bounds for heat and frost stress scoring.
- **USGS 3DEP & FCC API:** 10-meter digital elevation model (via OpenTopoData) for field slope and terrain characterization, and FCC Census Block API for geographic boundary mapping.
- **University Extension & Agronomic Research (K-State, SARE, NDSU, Dryad):** K-State MF2586 nitrogen fertilizer equations and previous-crop adjustments, SARE Handbook 9 cover crop nitrogen dynamics, NDSU A1995 disease-break intervals, Dryad crop nutrient contents, and peer-reviewed continuous cropping penalty studies (Seifert et al. 2017, Salvagiotti et al. 2008).
