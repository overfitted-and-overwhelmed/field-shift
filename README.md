# AGRIscora

**Team:** Overfitted and Overwhelmed  
**NASA Space Apps Challenge:** Field Shift  

## Overview
**AGRIscora** is a crop rotation scoring and decision-support tool that helps farmers adapt their fields to a changing climate. It evaluates and ranks multi-year crop rotations across water demand, climate risk, nitrogen requirements, and soil health.

## What We Built
- **Crop Scorer:** Models multi-year rotation performance, calculating irrigation needs (FAO-56 water balance), climate risk (heat and frost stress from temperature bounds), nitrogen dynamics, and erosion risk (bare soil days).
- **Rotation Explorer:** Compiles multi-year rotation metrics, seasonal yields, and monthly water/risk breakdowns with complete data provenance.
- **Farmer Advisor & MCP Server:** An interactive decision-support interface and Model Context Protocol (MCP) server that explains rotation trade-offs and allows farmers to re-rank candidate rotations based on their specific priorities (e.g., water savings vs. soil health).

## NASA Data & Resources
- **NASA POWER (Prediction Of Worldwide Energy Resources):** Daily meteorological data (precipitation, $T_{min}$, $T_{max}$, $T_{mean}$, solar radiation, and relative humidity) from 1991 to 2025.
- **Climate & Water Stress Modeling:** NASA POWER daily weather time-series are used to compute reference evapotranspiration ($ET_0$), historical water deficits, daily crop water demand ($ET_c$), and growth-stage heat/cold stress probabilities.

## External Data & Resources
- **USDA NRCS (SSURGO & NCSS):** High-resolution soil profile data (available water capacity, organic matter, texture) to calibrate root-zone water storage.
- **USDA NASS (CDL & Quick Stats):** Cropland Data Layer history for field-level cropping history, plus regional yield and price baselines.
- **FAO (FAO-56 & Ecocrop):** Stage-specific crop coefficients ($K_c$) for evapotranspiration modeling and temperature bounds for climate risk.
- **USGS 3DEP (via OpenTopoData):** 10-meter digital elevation data for field slope and terrain modeling.
- **University Extension & Agronomic Research (K-State MF2586, SARE, NDSU):** Nitrogen fertilizer recommendation equations, cover crop credits, continuous cropping yield penalties, and rotation intervals.
