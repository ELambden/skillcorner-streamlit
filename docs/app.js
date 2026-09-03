fetch("data/dashboard-data.json")
  .then((response) => response.ok ? response.json() : null)
  .then((payload) => {
    if (!payload) return;
    const scope = payload.scope || {};
    document.getElementById("players-count").textContent = Number(scope.players || 0).toLocaleString();
    document.getElementById("teams-count").textContent = Number(scope.teams || 0).toLocaleString();
    document.getElementById("matches-count").textContent = Number(scope.matches || 0).toLocaleString();
    document.getElementById("events-count").textContent = Number(scope.eventSample || 0).toLocaleString();
    document.getElementById("streamlit-frame").src = payload.streamlitAppUrl;
    document.querySelector(".source-line").textContent = `${Number(scope.players || 0).toLocaleString()} consolidated players · ${Number(scope.eventSample || 0).toLocaleString()} dynamic actions · ${Number(scope.offBallRuns || 0).toLocaleString()} off-ball runs`;
  })
  .catch(() => {});
