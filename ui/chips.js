(() => {
  const FAMILY = {
    inside_zone: 'run', outside_zone: 'run', power_counter: 'run',
    quick_game: 'pass', bunch_mesh: 'pass', vertical_shot: 'pass',
    rpo_glance: 'trick', play_action_flood: 'trick', screen: 'trick', bootleg: 'trick',
    base_cover3: 'coverage', cover3_match: 'coverage', quarters_match: 'coverage',
    cover1_man: 'coverage', two_high_shell: 'coverage', redzone_bracket: 'coverage', trap_coverage: 'coverage',
    zero_pressure: 'pressure', simulated_pressure: 'pressure',
    bear_front: 'front',
  };
  const familyOf = id => FAMILY[String(id || '').toLowerCase()] || null;
  const chipClassFor = id => {
    const family = familyOf(id);
    return family ? `chip chip--${family}` : 'chip';
  };
  const tierChipClass = tierNum => {
    const n = Number(tierNum);
    if (n === 1) return 'chip chip--tier-1';
    if (n === 2) return 'chip chip--tier-2';
    return 'chip chip--tier-0';
  };
  const tierNumberFromKey = key =>
    key === 'remote_endpoint' ? 2 : key === 'prompt_policy' ? 1 : 0;
  const seedDotClass = result =>
    result === 'touchdown' ? 'seed-dot seed-dot--touchdown'
      : result === 'stopped' ? 'seed-dot seed-dot--stopped'
        : 'seed-dot';
  const sparklineClass = (base, result) =>
    result === 'touchdown' ? `${base} ${base}--positive`
      : result === 'stopped' ? `${base} ${base}--negative`
        : base;
  window.CBChips = { familyOf, chipClassFor, tierChipClass, tierNumberFromKey, seedDotClass, sparklineClass };
})();
