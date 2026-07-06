// Moli — carte chat de l'assistant (charte « Le Relevé »).
//
// Tourne dans le navigateur de l'occupant. Ne connaît AUCUN secret : elle
// parle aux vues internes HA `/api/moli_ai/*` via hass.callApi (auth de session
// HA), qui relaient vers le central en gardant l'agent_token côté serveur.
//
// Flux :
//   - envoi d'un message → POST moli_ai/converse → { response, action? }
//   - si `action` (niveau 2) → carte de confirmation (Confirmer / Annuler)
//     → POST moli_ai/action/{id} { op } → { message }
//   - « Annuler la dernière action » → GET moli_ai/actions → POST … { op:'rollback' }
(() => {
  if (customElements.get("moli-chat-card")) return;

  const CSS = `
:host { display:block; }
.wrap {
  display:flex; flex-direction:column; height:100%;
  min-height: 70vh; max-width: 760px; margin: 0 auto;
  font-family: "Archivo", var(--primary-font-family, system-ui), sans-serif;
  color: var(--primary-text-color, #161510);
}
.head {
  display:flex; align-items:center; gap:10px;
  padding: 14px 18px; border-bottom: 2px solid var(--primary-text-color, #161510);
}
.head .dot { width:10px; height:10px; border-radius:50%; background:#FFD337; box-shadow:0 0 0 3px rgba(255,211,55,.25); }
.head h2 { font-size: 1rem; letter-spacing:.06em; text-transform:uppercase; margin:0; font-weight:700; }
.head .sub { font-family: "JetBrains Mono", ui-monospace, monospace; font-size:.7rem; opacity:.6; margin-left:auto; }
.log { flex:1; overflow-y:auto; padding: 18px; display:flex; flex-direction:column; gap:12px; }
.msg { max-width: 82%; padding: 10px 13px; border-radius: 4px; line-height:1.45; font-size:.95rem; white-space:pre-wrap; word-wrap:break-word; }
.msg.me { align-self:flex-end; background: var(--primary-text-color, #161510); color: var(--card-background-color, #F2F0EA); }
.msg.moli { align-self:flex-start; background: color-mix(in srgb, var(--primary-text-color,#161510) 6%, transparent); border:1px solid color-mix(in srgb, var(--primary-text-color,#161510) 14%, transparent); }
.msg.sys { align-self:center; font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.72rem; opacity:.55; }
.confirm { align-self:flex-start; max-width:82%; border:2px solid #FFD337; border-radius:4px; padding:12px 14px; background: color-mix(in srgb, #FFD337 10%, transparent); }
.confirm p { margin:0 0 10px; font-size:.92rem; }
.confirm .row { display:flex; gap:8px; }
button {
  font-family: inherit; font-size:.8rem; letter-spacing:.04em; text-transform:uppercase;
  border:2px solid var(--primary-text-color,#161510); background:transparent; color:inherit;
  padding:7px 14px; border-radius:3px; cursor:pointer; transition: transform .12s ease, background .12s ease;
}
button:hover { background: color-mix(in srgb, var(--primary-text-color,#161510) 8%, transparent); }
button:active { transform: scale(.97); }
button.primary { background:#FFD337; border-color:#FFD337; color:#161510; font-weight:700; }
button:disabled { opacity:.4; cursor:default; }
.bar { display:flex; gap:8px; padding: 12px 18px; border-top: 2px solid var(--primary-text-color,#161510); }
.bar input { flex:1; font-family:inherit; font-size:.95rem; padding:10px 12px; border:1px solid color-mix(in srgb, var(--primary-text-color,#161510) 30%, transparent); border-radius:3px; background: var(--card-background-color, #F2F0EA); color:inherit; }
.bar input:focus { outline:2px solid #FFD337; outline-offset:0; }
.foot { display:flex; justify-content:flex-end; padding: 0 18px 12px; }
.foot button { font-size:.68rem; border-width:1px; opacity:.7; }
.typing { font-family:"JetBrains Mono",ui-monospace,monospace; font-size:.72rem; opacity:.5; align-self:flex-start; }
`;

  class MoliChatCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._busy = false;
      this._greeted = false;
    }

    setConfig(config) {
      this._config = config || {};
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._built) this._build();
      if (!this._greeted) {
        this._greeted = true;
        this._addMsg(
          "moli",
          "Bonjour, je suis Moli, votre assistant. Posez-moi une question sur votre maison, ou demandez-moi d'agir (renommer un indicateur, ajouter un appareil…).",
        );
      }
    }

    getCardSize() {
      return 10;
    }

    _build() {
      this._built = true;
      const style = document.createElement("style");
      style.textContent = CSS;
      const wrap = document.createElement("div");
      wrap.className = "wrap";
      wrap.innerHTML = `
        <div class="head">
          <span class="dot"></span>
          <h2>Moli — Assistant</h2>
          <span class="sub">en direct</span>
        </div>
        <div class="log" id="log"></div>
        <div class="foot"><button id="undo">Annuler la dernière action</button></div>
        <div class="bar">
          <input id="in" type="text" placeholder="Écrivez à Moli…" autocomplete="off" />
          <button id="send" class="primary">Envoyer</button>
        </div>`;
      this.shadowRoot.append(style, wrap);
      this._log = wrap.querySelector("#log");
      this._input = wrap.querySelector("#in");
      const send = wrap.querySelector("#send");
      send.addEventListener("click", () => this._onSend());
      this._input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") this._onSend();
      });
      wrap.querySelector("#undo").addEventListener("click", () => this._rollbackLast());
    }

    _addMsg(kind, text) {
      const el = document.createElement("div");
      el.className = "msg " + kind;
      el.textContent = text;
      this._log.appendChild(el);
      this._log.scrollTop = this._log.scrollHeight;
      return el;
    }

    async _onSend() {
      const text = (this._input.value || "").trim();
      if (!text || this._busy) return;
      this._input.value = "";
      this._addMsg("me", text);
      this._setBusy(true);
      const typing = document.createElement("div");
      typing.className = "typing";
      typing.textContent = "Moli réfléchit…";
      this._log.appendChild(typing);
      this._log.scrollTop = this._log.scrollHeight;
      try {
        const res = await this._hass.callApi("POST", "moli_ai/converse", { message: text });
        typing.remove();
        this._addMsg("moli", res.response || "…");
        if (res.action && res.action.id) this._renderConfirm(res.action);
      } catch (e) {
        typing.remove();
        this._addMsg("sys", "Moli est injoignable pour le moment.");
      } finally {
        this._setBusy(false);
      }
    }

    _renderConfirm(action) {
      const box = document.createElement("div");
      box.className = "confirm";
      const p = document.createElement("p");
      p.textContent = "Confirmez-vous : " + (action.summary || "cette action") + " ?";
      const row = document.createElement("div");
      row.className = "row";
      const yes = document.createElement("button");
      yes.className = "primary";
      yes.textContent = "Confirmer";
      const no = document.createElement("button");
      no.textContent = "Annuler";
      row.append(yes, no);
      box.append(p, row);
      this._log.appendChild(box);
      this._log.scrollTop = this._log.scrollHeight;

      yes.addEventListener("click", async () => {
        yes.disabled = no.disabled = true;
        try {
          const r = await this._hass.callApi("POST", "moli_ai/action/" + action.id, { op: "confirm" });
          box.remove();
          this._addMsg("moli", r.message || "C'est fait.");
        } catch {
          this._addMsg("sys", "L'action a échoué.");
          yes.disabled = no.disabled = false;
        }
      });
      no.addEventListener("click", async () => {
        yes.disabled = no.disabled = true;
        try {
          await this._hass.callApi("POST", "moli_ai/action/" + action.id, { op: "reject" });
        } catch {
          /* ignore */
        }
        box.remove();
        this._addMsg("sys", "Action annulée.");
      });
    }

    async _rollbackLast() {
      if (this._busy) return;
      this._setBusy(true);
      try {
        const res = await this._hass.callApi("GET", "moli_ai/actions");
        const last = (res.actions || []).find((a) => a.canRollback);
        if (!last) {
          this._addMsg("sys", "Aucune action récente à annuler.");
          return;
        }
        const r = await this._hass.callApi("POST", "moli_ai/action/" + last.id, { op: "rollback" });
        this._addMsg("moli", r.message || "C'est annulé.");
      } catch {
        this._addMsg("sys", "Impossible d'annuler pour le moment.");
      } finally {
        this._setBusy(false);
      }
    }

    _setBusy(b) {
      this._busy = b;
      if (this._input) this._input.disabled = b;
    }
  }

  customElements.define("moli-chat-card", MoliChatCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "moli-chat-card",
    name: "Moli — Assistant",
    description: "Chat de l'assistant Moli AI (actions confirmées).",
  });
})();
