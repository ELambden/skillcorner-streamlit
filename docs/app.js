const pct = (value) => `${Number(value || 0).toFixed(0)}%`;

function playerCard(player) {
  return `
    <article class="player-card">
      <strong>${player.player_short_name || player.player_name}</strong>
      <p>${player.team_name} · ${player.position_group} · ${player.archetype}</p>
      <div class="bars">
        <div class="bar" title="Profile"><i style="width:${pct(player.profile_score)}"></i></div>
        <div class="bar" title="Off-ball"><i style="width:${pct(player.off_ball_threat_score)}"></i></div>
        <div class="bar" title="Passing"><i style="width:${pct(player.passing_progression_score)}"></i></div>
      </div>
    </article>
  `;
}

function teamCards(rows) {
  const grouped = new Map();
  rows.forEach((row) => {
    const key = row.team_name;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(row);
  });
  return [...grouped.entries()].slice(0, 6).map(([team, phases]) => {
    const top = phases.sort((a, b) => Number(b.phase_minutes || 0) - Number(a.phase_minutes || 0)).slice(0, 3);
    return `
      <article class="team-card">
        <strong>${team}</strong>
        ${top.map((phase) => `<p><span>${phase.phase_type}</span>${Number(phase.phase_share_pct || 0).toFixed(1)}% phase share</p>`).join("")}
      </article>
    `;
  }).join("");
}

function matchCard(match) {
  return `
    <article class="match-card">
      <span>${match.date_time?.slice(0, 10) || ""}</span>
      <strong>${match.match_label}</strong>
      <p>${match.score} · ${Number(match.events || 0).toLocaleString()} events · ${Number(match.dangerous_events || 0).toLocaleString()} dangerous</p>
      <p>Tracking: ${match.tracking_status}</p>
    </article>
  `;
}

fetch("data/dashboard-data.json")
  .then((response) => response.ok ? response.json() : null)
  .then((payload) => {
    if (!payload) return;
    document.getElementById("players-count").textContent = Number(payload.scope.players || 0).toLocaleString();
    document.getElementById("teams-count").textContent = Number(payload.scope.teams || 0).toLocaleString();
    document.getElementById("matches-count").textContent = Number(payload.scope.matches || 0).toLocaleString();
    document.getElementById("events-count").textContent = Number(payload.scope.eventSample || 0).toLocaleString();
    document.getElementById("top-player-grid").innerHTML = payload.topPlayers.slice(0, 9).map(playerCard).join("");
    document.getElementById("team-style-grid").innerHTML = teamCards(payload.teamStyle);
    document.getElementById("match-grid").innerHTML = payload.matches.slice(0, 6).map(matchCard).join("");
    document.getElementById("streamlit-frame").src = payload.streamlitAppUrl;
    document.querySelector(".source-line").textContent = `Static snapshot: ${payload.scope.players} players, ${payload.scope.matches} matches, ${payload.scope.eventSample} sampled dynamic events.`;
  })
  .catch(() => {});
