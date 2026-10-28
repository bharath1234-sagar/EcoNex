# EcoNex - Carbon Intelligence & Reduction Platform

A full-stack sustainability management and greenhouse gas accounting system featuring user authentication, custom personas, persistent simulation, and actionable reduction recommendations.

## Features
- **Full Authentication**: Sign In & Register (with secure password hashing) or Instant Demo Access.
- **6 Operational Personas**: Household, Urban Professional, Student / Hosteller, College Admin, Farmer & Dairy Producer, and Industrial Manufacturing.
- **Actionable Emission Control Recommendations**: Dynamic prioritized recommendations targeting your highest emission source with estimated kg CO₂e and monetary savings.
- **Persistent What-If Reduction Simulator**: Real-time sliders backed by localStorage and database synchronization.
- **AI Sustainability Advisor**: Intelligent assistant providing reduction strategies, official emission factors, and personalized advice.
- **Real User Leaderboard**: Dynamically computed from the database based on real earned EcoPoints.

## How to Run
```powershell
python -m pip install -r requirements.txt
python app.py