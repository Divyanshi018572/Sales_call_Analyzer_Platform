# Streamlit Dashboard Component

**What it does:**
Provides a responsive web interface for FitNova Call Analytics, organized into three distinct views mapping to corporate roles: Sales Director (organization-wide), Team Leader (team rollups and dispute resolutions), and Advisor (personal scorecards, call detail transcripts, and dispute filing).

**Why built this way:**
- **Single-Service Role Navigation**: Employs a sidebar role selector enabling testing of all three perspectives in a single, lightweight application.
- **RESTful Coupling**: Fetches statistics, transcripts, and list resources on-the-fly using standard `requests` HTTP calls to the FastAPI backend, decoupling the frontend completely from database dependencies.
- **Premium Glassmorphic Aesthetics**: Injects modern `Outfit` typography and semi-translucent styled cards (`rgba` backgrounds) that render elegantly in both light and dark modes.

**Inputs / outputs:**
- **Input**: User actions (e.g., button clicks to trigger ingestion/processing, dropdown selectors, filing dispute notes, and resolving active disputes).
- **Output**: Visual representation of call logs, color-coded transcript bubbles, performance charts, and real-time scorecard updates.

**Edge cases handled here:**
- **Empty Database State**: Paired with backend startup seeding, the dropdown filters are guaranteed to load functional options (org, team, and advisors) on first launch.
- **API Disconnections**: Displays clear error toasts in the sidebar if the target FastAPI host is unreachable, preventing unhandled Streamlit runtime exceptions.

**Known gaps / what I'd do with more time:**
- Integrate **Plotly** or **Chart.js** to render interactive radar charts showing multi-dimensional quality trends over time.
- Implement **virtualized pagination** or lazy-loading for the Sales Director's call history table to maintain fast loading speeds when call volumes scale to thousands of records.
