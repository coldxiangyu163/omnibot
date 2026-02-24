/**
 * OmniBot Web Widget — embed on any website.
 * Usage: <script src="/static/widget/widget.js"></script>
 */
(function () {
  const STYLE = `
    #omnibot-toggle { position:fixed; bottom:24px; right:24px; width:56px; height:56px;
      border-radius:50%; background:#2563eb; color:#fff; border:none; cursor:pointer;
      font-size:24px; box-shadow:0 4px 12px rgba(0,0,0,.15); z-index:9999; }
    #omnibot-panel { position:fixed; bottom:96px; right:24px; width:380px; height:520px;
      border-radius:16px; background:#fff; box-shadow:0 8px 32px rgba(0,0,0,.18);
      display:none; flex-direction:column; z-index:9999; overflow:hidden; font-family:system-ui,sans-serif; }
    #omnibot-header { background:#2563eb; color:#fff; padding:16px; font-weight:600; font-size:15px; }
    #omnibot-messages { flex:1; overflow-y:auto; padding:12px; }
    .omnibot-msg { margin:8px 0; padding:10px 14px; border-radius:12px; max-width:80%; font-size:14px; line-height:1.5; }
    .omnibot-bot { background:#f1f5f9; align-self:flex-start; }
    .omnibot-user { background:#2563eb; color:#fff; align-self:flex-end; margin-left:auto; }
    #omnibot-input-row { display:flex; border-top:1px solid #e2e8f0; padding:8px; }
    #omnibot-input { flex:1; border:none; outline:none; padding:8px 12px; font-size:14px; }
    #omnibot-send { background:#2563eb; color:#fff; border:none; padding:8px 16px;
      border-radius:8px; cursor:pointer; font-size:14px; }
  `;
  const style = document.createElement('style');
  style.textContent = STYLE;
  document.head.appendChild(style);

  const toggle = document.createElement('button');
  toggle.id = 'omnibot-toggle';
  toggle.textContent = '\uD83D\uDCAC';
  document.body.appendChild(toggle);

  const panel = document.createElement('div');
  panel.id = 'omnibot-panel';
  panel.innerHTML = '<div id="omnibot-header">\uD83E\uDD16 OmniBot</div>'
    + '<div id="omnibot-messages" style="display:flex;flex-direction:column;"></div>'
    + '<div id="omnibot-input-row">'
    + '<input id="omnibot-input" placeholder="Type a message..." />'
    + '<button id="omnibot-send">Send</button></div>';
  document.body.appendChild(panel);

  var ws, isOpen = false;
  var msgs = panel.querySelector('#omnibot-messages');
  var input = panel.querySelector('#omnibot-input');
  var send = panel.querySelector('#omnibot-send');

  function addMsg(text, cls) {
    var d = document.createElement('div');
    d.className = 'omnibot-msg ' + cls;
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function connect() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(proto + '://' + location.host + '/ws/chat');
    ws.onmessage = function(e) {
      var data = JSON.parse(e.data);
      if (data.type === 'message') addMsg(data.text, 'omnibot-bot');
    };
  }

  function doSend() {
    var text = input.value.trim();
    if (!text || !ws) return;
    addMsg(text, 'omnibot-user');
    ws.send(JSON.stringify({ text: text }));
    input.value = '';
  }

  toggle.onclick = function() {
    isOpen = !isOpen;
    panel.style.display = isOpen ? 'flex' : 'none';
    if (isOpen && !ws) connect();
  };
  send.onclick = doSend;
  input.onkeydown = function(e) { if (e.key === 'Enter') doSend(); };
})();
