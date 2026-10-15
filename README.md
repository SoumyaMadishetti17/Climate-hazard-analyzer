# Climate Hazard Trend Analyzer

A full-stack climate analysis application that detects historical heatwaves and analyzes their frequency, duration, intensity, and long-term trends using historical weather data.

**Live Demo:** https://climate-hazard-analyzer-mu.vercel.app/  
**Backend:** https://climate-hazard-analyzer-o8w5.onrender.com

## Features

- Search for geographic locations.
- Retrieve historical daily maximum temperatures.
- Detect heatwave events using a calendar-day percentile threshold.
- Analyze annual event counts, heatwave days, event duration, and intensity.
- Visualize historical trends and rolling averages.
- Evaluate trends using Mann–Kendall, Sen's slope, and ordinary least squares (OLS), where supported by the implementation.
- Cache analysis results to reduce repeated upstream requests.
- Validate input data and apply API rate limits.

## Technology Stack

- **Frontend:** React, Vite, Chart.js, Leaflet
- **Backend:** Python, FastAPI, Pydantic, Uvicorn
- **Database:** File-based storage by default; MongoDB support when configured
- **Weather data:** Open-Meteo Historical Weather API
- **Geocoding:** Open-Meteo Geocoding API
- **Deployment:** Vercel and Render

## Architecture

```text
React frontend
     |
     v
FastAPI backend
     |
     +----> Geocoding API
     |
     +----> Historical Weather API
     |
     +----> Cached raw data and analysis results
             (file-based storage or MongoDB)
```

## Getting Started

### Prerequisites

- Python compatible with the backend dependencies
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/SoumyaMadishetti17/Climate-hazard-analyzer.git
cd Climate-hazard-analyzer
```

### 2. Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive API documentation: `http://localhost:8000/docs`.

### 3. Run the frontend

Open a separate terminal:

```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL shown in the terminal.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/health` | Backend health check |
| `/api/geocode?q=` | Search for geographic locations |
| `/api/analysis` | Retrieve climate analysis |

The analysis endpoint accepts location coordinates, a date range, and a hazard type according to the backend's supported request parameters.

## Data Sources

- **Open-Meteo Historical Weather API:** Historical weather data, including daily maximum temperature.
- **Open-Meteo Geocoding API:** Geographic location search.

The availability and coverage of data depend on the selected location and requested period.

## Heatwave Detection

The intended detection approach identifies heatwave events as at least three consecutive days with daily maximum temperatures above the calendar-day 95th percentile, using a seasonal reference window and a fixed baseline.

The analysis can summarize event frequency, heatwave days, event duration, intensity, and long-term trends. Consult the implementation and API responses for the exact calculation details.

## Limitations

- Heatwave analysis is the implemented hazard; drought and heavy-rainfall analysis are not yet available.
- The current analysis uses a geographic grid point rather than averaging a user-drawn region.
- Daily maximum temperature alone does not capture humidity, nighttime temperatures, or a complete heat-index assessment.
- Browser-based printing may be used for PDF output; dedicated PDF generation and CSV export should not be assumed.
- Statistical methods and data-quality checks should be validated against the current implementation before relying on results.
- External API availability and deployment resource limits may affect response times.

## Future Improvements

- Add drought and heavy-rainfall analysis.
- Support map-based region selection and area averaging.
- Add CSV export and dedicated PDF generation.
- Improve caching and rate limiting for multi-instance deployments.
- Expand automated testing and continuous integration.

## AI-Assisted Development

Claude AI was used to assist with the initial project scaffold and code generation. ChatGPT was used for technical guidance, troubleshooting, and deployment assistance. AI-generated code should be reviewed and tested before being relied upon.

## License

No license has been specified. Add a license file if you intend to distribute the project for reuse.
