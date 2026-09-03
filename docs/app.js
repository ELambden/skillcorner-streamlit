const pct = (value) => `${Number(value || 0).toFixed(0)}%`;
const labelFrom = (labels, value) => labels?.[value] || String(value || "").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());

function playerCard(player) {
  const minutes = Number(player.minutes || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
  const contexts = Number(player.profile_context_count || 0);
  return `
    <article class="player-card">
      <strong>${player.player_short_name || player.player_name}</strong>
      <p>${player.team_name} · ${player.position_group} · ${player.archetype}</p>
      <p>${minutes} evidence minutes · ${contexts} context${contexts === 1 ? "" : "s"}</p>
      <div class="bars">
        <div class="bar" title="Overall profile"><i style="width:${pct(player.profile_score)}"></i></div>
        <div class="bar" title="Attacking movement"><i style="width:${pct(player.off_ball_threat_score)}"></i></div>
        <div class="bar" title="Passing progression"><i style="width:${pct(player.passing_progression_score)}"></i></div>
      </div>
    </article>
  `;
}

function teamCards(rows, labels) {
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
        ${top.map((phase) => `<p><span>${labelFrom(labels, phase.phase_type)}</span>${Number(phase.phase_share_pct || 0).toFixed(1)}% phase share</p>`).join("")}
      </article>
    `;
  }).join("");
}

function archetypeCards(definitions) {
  return Object.entries(definitions || {}).map(([name, item]) => `
    <article class="archetype-card">
      <strong>${name}</strong>
      <p>${item.short}</p>
      <span>Priority evidence</span>
      <p>${(item.prioritised || []).join("; ")}</p>
    </article>
  `).join("");
}

function matchCard(match, labels) {
  return `
    <article class="match-card">
      <span>${match.date_time?.slice(0, 10) || ""}</span>
      <strong>${match.match_label}</strong>
      <p>${match.score} · ${Number(match.events || 0).toLocaleString()} actions · ${Number(match.off_ball_runs || 0).toLocaleString()} off-ball runs</p>
      <p>${Number(match.high_intensity_runs || 0).toLocaleString()} high-intensity runs · ${Number(match.xthreat_total || 0).toFixed(2)} threat value</p>
      <p>${labelFrom(labels, match.tracking_status)}</p>
    </article>
  `;
}

function runCard(run, subtypeLabels, speedLabels) {
  return `
    <article class="run-card">
      <span>${run.match_label}</span>
      <strong>${run.player_name}</strong>
      <p>${run.team_shortname} · ${labelFrom(subtypeLabels, run.event_subtype)} · ${labelFrom(speedLabels, run.speed_avg_band)}</p>
      <p>${Number(run.distance_covered || 0).toFixed(1)}m · ${Number(run.xthreat || 0).toFixed(3)} xThreat · ${Number(run.received || 0) ? "received" : "not received"}</p>
    </article>
  `;
}

fetch("data/dashboard-data.json")
  .then((response) => response.ok ? response.json() : null)
  .then((payload) => {
    if (!payload) return;
    const labels = payload.displayLabels || {};
    document.getElementById("players-count").textContent = Number(payload.scope.players || 0).toLocaleString();
    document.getElementById("teams-count").textContent = Number(payload.scope.teams || 0).toLocaleString();
    document.getElementById("matches-count").textContent = Number(payload.scope.matches || 0).toLocaleString();
    document.getElementById("events-count").textContent = Number(payload.scope.eventSample || 0).toLocaleString();
    document.getElementById("top-player-grid").innerHTML = payload.topPlayers.slice(0, 9).map(playerCard).join("");
    document.getElementById("team-style-grid").innerHTML = teamCards(payload.teamStyle, labels.phases);
    document.getElementById("archetype-grid").innerHTML = archetypeCards(payload.archetypeDefinitions);
    document.getElementById("match-grid").innerHTML = payload.matches.slice(0, 6).map((match) => matchCard(match, labels.tracking)).join("");
    document.getElementById("run-grid").innerHTML = (payload.topOffBallRuns || []).slice(0, 6).map((run) => runCard(run, labels.runSubtypes, labels.speedBands)).join("");
    document.getElementById("streamlit-frame").src = payload.streamlitAppUrl;
    document.querySelector(".source-line").textContent = `Static snapshot: ${payload.scope.players} consolidated players, ${payload.scope.matches} matches, ${Number(payload.scope.eventSample || 0).toLocaleString()} dynamic actions, ${Number(payload.scope.offBallRuns || 0).toLocaleString()} off-ball runs.`;
  })
  .catch(() => {});
