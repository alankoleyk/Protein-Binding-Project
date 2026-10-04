/* Molecular rendering only. Scientific calculations belong to the Python backend. */
new QWebChannel(qt.webChannelTransport, ({ objects: { bridge } }) => {
  const keyOf = (key) => `${key.chain}:${key.number}:${key.insertion}`;
  const atomKey = (atom) => `${atom.chain}:${atom.resi}:${(atom.icode || '').trim()}`;
  let chains = [];
  let originalCamera;
  let selected;
  let viewer;

  function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.hidden = false;
    bridge.load_failed(message);
  }

  function loadScene(serialized) {
    const scene = JSON.parse(serialized);
    chains = scene.chains;
    const chainIds = new Set(chains.map((chain) => chain.id));
    const residueKeys = new Set(scene.residues.map(keyOf));
    const pdb = scene.pdb.split(/\r?\n/).filter((line) => {
      if (!/^(ATOM  |HETATM|TER   )/.test(line)) return true;
      return line.startsWith('ATOM') && chainIds.has(line[21]) && [' ', 'A'].includes(line[16]);
    }).join('\n');
    viewer.clear();
    viewer.addModel(pdb, 'pdb');
    for (const chain of chains) {
      viewer.setStyle({ chain: chain.id }, { cartoon: { color: chain.color } });
    }
    viewer.setClickable({ predicate: (atom) => residueKeys.has(atomKey(atom)) }, true, (atom) => {
      bridge.residue_picked(atom.chain, atom.resi, (atom.icode || '').trim());
    });
    viewer.zoomTo();
    viewer.rotate(25, 'y');
    viewer.rotate(-15, 'x');
    viewer.zoom(1.08);
    viewer.render();
    originalCamera = viewer.getView();
    document.getElementById('complex').textContent = `${scene.code}  /  ${[...chainIds].join(' + ')}`;
    bridge.scene_loaded();
  }

  function applyStyle(serialized) {
    const state = JSON.parse(serialized);
    selected = state.selected;
    const interfaceKeys = new Set(state.interface.map(keyOf));
    viewer.removeAllSurfaces();
    viewer.removeAllLabels();
    viewer.setStyle({}, {});
    for (const chain of chains) {
      viewer.setStyle({ chain: chain.id }, state.representation === 'sticks'
        ? { stick: { color: chain.color, radius: 0.15 } }
        : { cartoon: { color: chain.color, opacity: state.representation === 'surface' ? 0.3 : 1 } });
      if (state.representation === 'surface') {
        viewer.addSurface($3Dmol.SurfaceType.VDW,
          { color: chain.color, opacity: 0.8 }, { chain: chain.id });
      }
      if (state.highlight) {
        viewer.addStyle({ chain: chain.id, predicate: (atom) => interfaceKeys.has(atomKey(atom)) },
          { stick: { color: chain.color, radius: 0.16 } });
      }
    }
    const selection = { predicate: (atom) => atomKey(atom) === keyOf(selected) };
    viewer.addStyle(selection, {
      stick: { color: '#f2c477', radius: 0.25 },
      sphere: { color: '#f2c477', scale: 0.25 },
    });
    const atom = viewer.selectedAtoms(selection)[0];
    viewer.addLabel(`${atom.resn} ${selected.number}${selected.insertion} · ${selected.chain}`, {
      backgroundColor: '#242424', backgroundOpacity: 0.95,
      fontColor: '#dec491', fontSize: 11, borderColor: '#685c43', borderThickness: 1,
      inFront: true,
    }, selection);
    viewer.render();
  }

  function camera(command) {
    if (command === 'spin') viewer.spin('y', 0.4);
    if (command === 'pause') viewer.spin(false);
    if (command === 'zoom-in') viewer.zoom(1.2);
    if (command === 'zoom-out') viewer.zoom(0.8);
    if (command === 'focus') {
      viewer.zoomTo({ predicate: (atom) => atomKey(atom) === keyOf(selected) });
      viewer.zoom(0.55);
    }
    if (command === 'reset') {
      viewer.spin(false);
      viewer.setView(originalCamera);
    }
    viewer.render();
  }

  try {
    viewer = $3Dmol.createViewer(document.getElementById('molecule'), {
      backgroundColor: '#000000', antialias: true,
    });
    new ResizeObserver(() => viewer.resize()).observe(document.getElementById('molecule'));
    bridge.scene_changed.connect(loadScene);
    bridge.style_changed.connect(applyStyle);
    bridge.camera_command.connect(camera);
    window.proteinBinding = { viewer };
    bridge.ready();
  } catch (error) {
    showError(error.message);
  }
});
