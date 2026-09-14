"""Trechos de CSS, HTML e JS do visualizador (2D + 3D). Ver viewer.py."""

CSS_EXTRA = r'''
  /* ---------- abas 2D / 3D ---------- */
  .modos{display:flex; gap:2px; margin-right:14px}
  .modos button{
    font-family:var(--mono); font-size:11.5px; letter-spacing:.08em;
    text-transform:uppercase; border:1px solid var(--rule); background:var(--surface);
    color:var(--ink-soft); padding:6px 14px; cursor:pointer;
  }
  .modos button[aria-selected="true"]{
    background:var(--accent); border-color:var(--accent); color:#fff;
  }
  .modos button:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

  /* ---------- palco 3D ---------- */
  .stage3d{position:relative; overflow:hidden; background:var(--stage);
           height:min(72vh,660px); cursor:grab; touch-action:none}
  .stage3d.dragging{cursor:grabbing}
  .stage3d canvas{display:block; width:100%; height:100%}
  .hud{
    position:absolute; left:12px; bottom:12px; right:12px;
    display:flex; flex-wrap:wrap; gap:8px 16px; align-items:flex-end;
    pointer-events:none;
  }
  .hud > *{pointer-events:auto}
  .camadas{
    display:flex; flex-wrap:wrap; gap:4px; background:var(--surface);
    border:1px solid var(--rule); padding:6px; border-radius:2px;
  }
  .camadas label{
    display:flex; align-items:center; gap:5px; font-family:var(--mono);
    font-size:10.5px; letter-spacing:.04em; text-transform:uppercase;
    color:var(--ink-soft); cursor:pointer; padding:3px 6px;
  }
  .camadas input{accent-color:var(--accent); margin:0}
  .sol{
    background:var(--surface); border:1px solid var(--rule); padding:8px 10px;
    border-radius:2px; display:flex; flex-direction:column; gap:6px; min-width:210px;
  }
  .sol .linha{display:flex; align-items:center; gap:8px}
  .sol label{font-family:var(--mono); font-size:10px; letter-spacing:.1em;
             text-transform:uppercase; color:var(--ink-faint); min-width:52px}
  .sol input[type=range]{flex:1; accent-color:var(--accent); min-width:80px}
  .sol .val{font-family:var(--mono); font-size:11px; font-variant-numeric:tabular-nums;
            color:var(--ink); min-width:64px; text-align:right}
  .sol select{font-family:var(--mono); font-size:11px; border:1px solid var(--rule);
              background:var(--surface); color:var(--ink); padding:2px 4px; flex:1}
  .leitura{
    position:absolute; top:12px; left:12px; background:var(--surface);
    border:1px solid var(--rule); padding:7px 11px; border-radius:2px;
    font-family:var(--mono); font-size:11px; color:var(--ink); max-width:260px;
  }
  .leitura b{display:block; font-size:12px; margin-bottom:2px}
  .leitura span{color:var(--ink-soft)}

  /* ---------- cenas ---------- */
  .cenas{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:3px}
  .cenas button{
    width:100%; text-align:left; background:none; border:1px solid transparent;
    border-radius:2px; padding:7px 8px; cursor:pointer; color:inherit;
    font-family:inherit; font-size:12.5px; line-height:1.3;
  }
  .cenas button:hover{background:var(--rule-soft)}
  .cenas button[aria-current="true"]{background:var(--accent-soft); border-color:var(--accent)}
  .cenas .sub{display:block; font-family:var(--mono); font-size:10px;
              color:var(--ink-faint); letter-spacing:.04em; text-transform:uppercase}
  @media (max-width:860px){
    .cenas{flex-direction:row; overflow-x:auto; padding-bottom:8px; gap:8px;
           min-width:0}
    .cenas li{flex:0 0 190px; min-width:0}
  }

  /* ---------- barras e dicas por modo ---------- */
  /* a troca de aba esconde metade da interface com o atributo hidden; sem esta
     linha qualquer display: de autor (.barra, .cenas) vence o UA e o elemento
     escondido continua na tela */
  [hidden]{display:none!important}
  /* sem wrap a barra de 8 botoes media 443 px e empurrava a PAGINA INTEIRA num
     visor de 390: o caderno abria escorregado para o lado no telefone, e o
     sintoma parecia do indice de pranchas — que ja rolava sozinho e estava
     certo. Medir disse qual dos dois era */
  .barra{display:flex; gap:10px; align-items:center; flex-wrap:wrap}
  .rail .dica{margin:12px 0 0; font-family:var(--mono); font-size:10.5px;
              line-height:1.6; color:var(--ink-faint); letter-spacing:.02em}
  .notas3d dl{margin:0; display:grid; grid-template-columns:auto 1fr; gap:8px 16px}
  .notas3d dt{font-family:var(--mono); font-size:11.5px; color:var(--accent)}
  .notas3d dd{margin:0; font-size:13.5px; color:var(--ink-soft)}
'''

HTML_3D = r'''
      <div class="stage3d" id="stage3d" hidden>
        <div class="leitura" id="leitura3d"><b>Carregando o modelo…</b>
          <span>329 sólidos vindos do mesmo arquivo que gera as pranchas</span></div>
        <div class="hud">
          <div class="camadas" id="camadas"></div>
          <div class="sol">
            <div class="linha"><label for="solEpoca">Época</label>
              <select id="solEpoca">
                <option value="-23.45">Solstício de junho</option>
                <option value="0" selected>Equinócio</option>
                <option value="23.45">Solstício de dezembro</option>
              </select></div>
            <div class="linha"><label for="solHora">Hora</label>
              <input type="range" id="solHora" min="6" max="18" step="0.5" value="10">
              <span class="val" id="solVal">10:00</span></div>
            <div class="linha"><label for="corte">Corte</label>
              <input type="range" id="corte" min="0" max="6400" step="100" value="6400">
              <span class="val" id="corteVal">sem corte</span></div>
          </div>
        </div>
      </div>
'''
