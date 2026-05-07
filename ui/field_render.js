(() => {
  function fieldHtml(ballId = 'ball') {
    return `<div class="field">
      <div class="yard-rule y20"><span>20</span></div>
      <div class="yard-rule y15"><span>15</span></div>
      <div class="yard-rule y10"><span>10</span></div>
      <div class="yard-rule y5"><span>5</span></div>
      <div class="mid-rule"></div>
      <div class="endzone">End Zone</div>
      <div id="${ballId}" class="ball"></div>
    </div>`;
  }

  function positionBall(ball, yardline, terminalReason, reduced = false) {
    if (!ball) return;
    const clamped = Math.max(0, Math.min(25, Number(yardline)));
    ball.style.left = `${8 + ((25 - clamped) / 25) * 84}%`;
    ball.classList.toggle('touchdown', terminalReason === 'touchdown');
    if (!reduced) {
      ball.classList.remove('move');
      void ball.offsetWidth;
      ball.classList.add('move');
    }
  }

  function ordinal(value) {
    const n = Number(value || 1);
    if (n === 1) return '1st';
    if (n === 2) return '2nd';
    if (n === 3) return '3rd';
    return `${n}th`;
  }

  function downsText(play) {
    const pub = play?.public || {};
    if (pub.terminal_reason === 'touchdown') return 'TOUCHDOWN';
    const state = pub.next_state || {};
    return `${ordinal(state.down)} & ${state.distance} at ${state.yardline}`;
  }

  window.CBField = { fieldHtml, positionBall, downsText, ordinal };
})();
