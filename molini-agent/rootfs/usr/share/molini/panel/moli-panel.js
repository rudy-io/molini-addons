var Ue = Object.defineProperty;
var Ie = (t, e, r) => e in t ? Ue(t, e, { enumerable: !0, configurable: !0, writable: !0, value: r }) : t[e] = r;
var G = (t, e, r) => Ie(t, typeof e != "symbol" ? e + "" : e, r);
var B, g, Pe, S, ce, Se, Me, J, E, A, ze, oe, Y, ee, U = {}, I = [], Re = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, V = Array.isArray;
function $(t, e) {
  for (var r in e) t[r] = e[r];
  return t;
}
function ie(t) {
  t && t.parentNode && t.parentNode.removeChild(t);
}
function He(t, e, r) {
  var n, i, o, s = {};
  for (o in e) o == "key" ? n = e[o] : o == "ref" ? i = e[o] : s[o] = e[o];
  if (arguments.length > 2 && (s.children = arguments.length > 3 ? B.call(arguments, 2) : r), typeof t == "function" && t.defaultProps != null) for (o in t.defaultProps) s[o] === void 0 && (s[o] = t.defaultProps[o]);
  return j(t, s, n, i, null);
}
function j(t, e, r, n, i) {
  var o = { type: t, props: e, key: r, ref: n, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: i ?? ++Pe, __i: -1, __u: 0 };
  return i == null && g.vnode != null && g.vnode(o), o;
}
function X(t) {
  return t.children;
}
function T(t, e) {
  this.props = t, this.context = e;
}
function C(t, e) {
  if (e == null) return t.__ ? C(t.__, t.__i + 1) : null;
  for (var r; e < t.__k.length; e++) if ((r = t.__k[e]) != null && r.__e != null) return r.__e;
  return typeof t.type == "function" ? C(t) : null;
}
function Oe(t) {
  if (t.__P && t.__d) {
    var e = t.__v, r = e.__e, n = [], i = [], o = $({}, e);
    o.__v = e.__v + 1, g.vnode && g.vnode(o), le(t.__P, o, e, t.__n, t.__P.namespaceURI, 32 & e.__u ? [r] : null, n, r ?? C(e), !!(32 & e.__u), i), o.__v = e.__v, o.__.__k[o.__i] = o, Fe(n, o, i), e.__e = e.__ = null, o.__e != r && Ce(o);
  }
}
function Ce(t) {
  if ((t = t.__) != null && t.__c != null) return t.__e = t.__c.base = null, t.__k.some(function(e) {
    if (e != null && e.__e != null) return t.__e = t.__c.base = e.__e;
  }), Ce(t);
}
function de(t) {
  (!t.__d && (t.__d = !0) && S.push(t) && !R.__r++ || ce != g.debounceRendering) && ((ce = g.debounceRendering) || Se)(R);
}
function R() {
  try {
    for (var t, e = 1; S.length; ) S.length > e && S.sort(Me), t = S.shift(), e = S.length, Oe(t);
  } finally {
    S.length = R.__r = 0;
  }
}
function Ne(t, e, r, n, i, o, s, _, d, a, h) {
  var l, u, p, v, y, x, m, f = n && n.__k || I, P = e.length;
  for (d = qe(r, e, f, d, P), l = 0; l < P; l++) (p = r.__k[l]) != null && (u = p.__i != -1 && f[p.__i] || U, p.__i = l, x = le(t, p, u, i, o, s, _, d, a, h), v = p.__e, p.ref && u.ref != p.ref && (u.ref && se(u.ref, null, p), h.push(p.ref, p.__c || v, p)), y == null && v != null && (y = v), (m = !!(4 & p.__u)) || u.__k === p.__k ? (d = Ae(p, d, t, m), m && u.__e && (u.__e = null)) : typeof p.type == "function" && x !== void 0 ? d = x : v && (d = v.nextSibling), p.__u &= -7);
  return r.__e = y, d;
}
function qe(t, e, r, n, i) {
  var o, s, _, d, a, h = r.length, l = h, u = 0;
  for (t.__k = new Array(i), o = 0; o < i; o++) (s = e[o]) != null && typeof s != "boolean" && typeof s != "function" ? (typeof s == "string" || typeof s == "number" || typeof s == "bigint" || s.constructor == String ? s = t.__k[o] = j(null, s, null, null, null) : V(s) ? s = t.__k[o] = j(X, { children: s }, null, null, null) : s.constructor === void 0 && s.__b > 0 ? s = t.__k[o] = j(s.type, s.props, s.key, s.ref ? s.ref : null, s.__v) : t.__k[o] = s, d = o + u, s.__ = t, s.__b = t.__b + 1, _ = null, (a = s.__i = Be(s, r, d, l)) != -1 && (l--, (_ = r[a]) && (_.__u |= 2)), _ == null || _.__v == null ? (a == -1 && (i > h ? u-- : i < h && u++), typeof s.type != "function" && (s.__u |= 4)) : a != d && (a == d - 1 ? u-- : a == d + 1 ? u++ : (a > d ? u-- : u++, s.__u |= 4))) : t.__k[o] = null;
  if (l) for (o = 0; o < h; o++) (_ = r[o]) != null && !(2 & _.__u) && (_.__e == n && (n = C(_)), De(_, _));
  return n;
}
function Ae(t, e, r, n) {
  var i, o;
  if (typeof t.type == "function") {
    for (i = t.__k, o = 0; i && o < i.length; o++) i[o] && (i[o].__ = t, e = Ae(i[o], e, r, n));
    return e;
  }
  t.__e != e && (n && (e && t.type && !e.parentNode && (e = C(t)), r.insertBefore(t.__e, e || null)), e = t.__e);
  do
    e = e && e.nextSibling;
  while (e != null && e.nodeType == 8);
  return e;
}
function Be(t, e, r, n) {
  var i, o, s, _ = t.key, d = t.type, a = e[r], h = a != null && (2 & a.__u) == 0;
  if (a === null && _ == null || h && _ == a.key && d == a.type) return r;
  if (n > (h ? 1 : 0)) {
    for (i = r - 1, o = r + 1; i >= 0 || o < e.length; ) if ((a = e[s = i >= 0 ? i-- : o++]) != null && !(2 & a.__u) && _ == a.key && d == a.type) return s;
  }
  return -1;
}
function ue(t, e, r) {
  e[0] == "-" ? t.setProperty(e, r ?? "") : t[e] = r == null ? "" : typeof r != "number" || Re.test(e) ? r : r + "px";
}
function W(t, e, r, n, i) {
  var o, s;
  e: if (e == "style") if (typeof r == "string") t.style.cssText = r;
  else {
    if (typeof n == "string" && (t.style.cssText = n = ""), n) for (e in n) r && e in r || ue(t.style, e, "");
    if (r) for (e in r) n && r[e] == n[e] || ue(t.style, e, r[e]);
  }
  else if (e[0] == "o" && e[1] == "n") o = e != (e = e.replace(ze, "$1")), s = e.toLowerCase(), e = s in t || e == "onFocusOut" || e == "onFocusIn" ? s.slice(2) : e.slice(2), t.l || (t.l = {}), t.l[e + o] = r, r ? n ? r[A] = n[A] : (r[A] = oe, t.addEventListener(e, o ? ee : Y, o)) : t.removeEventListener(e, o ? ee : Y, o);
  else {
    if (i == "http://www.w3.org/2000/svg") e = e.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
    else if (e != "width" && e != "height" && e != "href" && e != "list" && e != "form" && e != "tabIndex" && e != "download" && e != "rowSpan" && e != "colSpan" && e != "role" && e != "popover" && e in t) try {
      t[e] = r ?? "";
      break e;
    } catch {
    }
    typeof r == "function" || (r == null || r === !1 && e[4] != "-" ? t.removeAttribute(e) : t.setAttribute(e, e == "popover" && r == 1 ? "" : r));
  }
}
function pe(t) {
  return function(e) {
    if (this.l) {
      var r = this.l[e.type + t];
      if (e[E] == null) e[E] = oe++;
      else if (e[E] < r[A]) return;
      return r(g.event ? g.event(e) : e);
    }
  };
}
function le(t, e, r, n, i, o, s, _, d, a) {
  var h, l, u, p, v, y, x, m, f, P, M, N, _e, F, K, k = e.type;
  if (e.constructor !== void 0) return null;
  128 & r.__u && (d = !!(32 & r.__u), o = [_ = e.__e = r.__e]), (h = g.__b) && h(e);
  e: if (typeof k == "function") try {
    if (m = e.props, f = k.prototype && k.prototype.render, P = (h = k.contextType) && n[h.__c], M = h ? P ? P.props.value : h.__ : n, r.__c ? x = (l = e.__c = r.__c).__ = l.__E : (f ? e.__c = l = new k(m, M) : (e.__c = l = new T(m, M), l.constructor = k, l.render = Xe), P && P.sub(l), l.state || (l.state = {}), l.__n = n, u = l.__d = !0, l.__h = [], l._sb = []), f && l.__s == null && (l.__s = l.state), f && k.getDerivedStateFromProps != null && (l.__s == l.state && (l.__s = $({}, l.__s)), $(l.__s, k.getDerivedStateFromProps(m, l.__s))), p = l.props, v = l.state, l.__v = e, u) f && k.getDerivedStateFromProps == null && l.componentWillMount != null && l.componentWillMount(), f && l.componentDidMount != null && l.__h.push(l.componentDidMount);
    else {
      if (f && k.getDerivedStateFromProps == null && m !== p && l.componentWillReceiveProps != null && l.componentWillReceiveProps(m, M), e.__v == r.__v || !l.__e && l.shouldComponentUpdate != null && l.shouldComponentUpdate(m, l.__s, M) === !1) {
        e.__v != r.__v && (l.props = m, l.state = l.__s, l.__d = !1), e.__e = r.__e, e.__k = r.__k, e.__k.some(function(H) {
          H && (H.__ = e);
        }), I.push.apply(l.__h, l._sb), l._sb = [], l.__h.length && s.push(l);
        break e;
      }
      l.componentWillUpdate != null && l.componentWillUpdate(m, l.__s, M), f && l.componentDidUpdate != null && l.__h.push(function() {
        l.componentDidUpdate(p, v, y);
      });
    }
    if (l.context = M, l.props = m, l.__P = t, l.__e = !1, N = g.__r, _e = 0, f) l.state = l.__s, l.__d = !1, N && N(e), h = l.render(l.props, l.state, l.context), I.push.apply(l.__h, l._sb), l._sb = [];
    else do
      l.__d = !1, N && N(e), h = l.render(l.props, l.state, l.context), l.state = l.__s;
    while (l.__d && ++_e < 25);
    l.state = l.__s, l.getChildContext != null && (n = $($({}, n), l.getChildContext())), f && !u && l.getSnapshotBeforeUpdate != null && (y = l.getSnapshotBeforeUpdate(p, v)), F = h != null && h.type === X && h.key == null ? We(h.props.children) : h, _ = Ne(t, V(F) ? F : [F], e, r, n, i, o, s, _, d, a), l.base = e.__e, e.__u &= -161, l.__h.length && s.push(l), x && (l.__E = l.__ = null);
  } catch (H) {
    if (e.__v = null, d || o != null) if (H.then) {
      for (e.__u |= d ? 160 : 128; _ && _.nodeType == 8 && _.nextSibling; ) _ = _.nextSibling;
      o[o.indexOf(_)] = null, e.__e = _;
    } else {
      for (K = o.length; K--; ) ie(o[K]);
      te(e);
    }
    else e.__e = r.__e, e.__k = r.__k, H.then || te(e);
    g.__e(H, e, r);
  }
  else o == null && e.__v == r.__v ? (e.__k = r.__k, e.__e = r.__e) : _ = e.__e = Ve(r.__e, e, r, n, i, o, s, d, a);
  return (h = g.diffed) && h(e), 128 & e.__u ? void 0 : _;
}
function te(t) {
  t && (t.__c && (t.__c.__e = !0), t.__k && t.__k.some(te));
}
function Fe(t, e, r) {
  for (var n = 0; n < r.length; n++) se(r[n], r[++n], r[++n]);
  g.__c && g.__c(e, t), t.some(function(i) {
    try {
      t = i.__h, i.__h = [], t.some(function(o) {
        o.call(i);
      });
    } catch (o) {
      g.__e(o, i.__v);
    }
  });
}
function We(t) {
  return typeof t != "object" || t == null || t.__b > 0 ? t : V(t) ? t.map(We) : t.constructor !== void 0 ? null : $({}, t);
}
function Ve(t, e, r, n, i, o, s, _, d) {
  var a, h, l, u, p, v, y, x = r.props || U, m = e.props, f = e.type;
  if (f == "svg" ? i = "http://www.w3.org/2000/svg" : f == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i || (i = "http://www.w3.org/1999/xhtml"), o != null) {
    for (a = 0; a < o.length; a++) if ((p = o[a]) && "setAttribute" in p == !!f && (f ? p.localName == f : p.nodeType == 3)) {
      t = p, o[a] = null;
      break;
    }
  }
  if (t == null) {
    if (f == null) return document.createTextNode(m);
    t = document.createElementNS(i, f, m.is && m), _ && (g.__m && g.__m(e, o), _ = !1), o = null;
  }
  if (f == null) x === m || _ && t.data == m || (t.data = m);
  else {
    if (o = f == "textarea" && m.defaultValue != null ? null : o && B.call(t.childNodes), !_ && o != null) for (x = {}, a = 0; a < t.attributes.length; a++) x[(p = t.attributes[a]).name] = p.value;
    for (a in x) p = x[a], a == "dangerouslySetInnerHTML" ? l = p : a == "children" || a in m || a == "value" && "defaultValue" in m || a == "checked" && "defaultChecked" in m || W(t, a, null, p, i);
    for (a in m) p = m[a], a == "children" ? u = p : a == "dangerouslySetInnerHTML" ? h = p : a == "value" ? v = p : a == "checked" ? y = p : _ && typeof p != "function" || x[a] === p || W(t, a, p, x[a], i);
    if (h) _ || l && (h.__html == l.__html || h.__html == t.innerHTML) || (t.innerHTML = h.__html), e.__k = [];
    else if (l && (t.innerHTML = ""), Ne(e.type == "template" ? t.content : t, V(u) ? u : [u], e, r, n, f == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, o, s, o ? o[0] : r.__k && C(r, 0), _, d), o != null) for (a = o.length; a--; ) ie(o[a]);
    _ && f != "textarea" || (a = "value", f == "progress" && v == null ? t.removeAttribute("value") : v != null && (v !== t[a] || f == "progress" && !v || f == "option" && v != x[a]) && W(t, a, v, x[a], i), a = "checked", y != null && y != t[a] && W(t, a, y, x[a], i));
  }
  return t;
}
function se(t, e, r) {
  try {
    if (typeof t == "function") {
      var n = typeof t.__u == "function";
      n && t.__u(), n && e == null || (t.__u = t(e));
    } else t.current = e;
  } catch (i) {
    g.__e(i, r);
  }
}
function De(t, e, r) {
  var n, i;
  if (g.unmount && g.unmount(t), (n = t.ref) && (n.current && n.current != t.__e || se(n, null, e)), (n = t.__c) != null) {
    if (n.componentWillUnmount) try {
      n.componentWillUnmount();
    } catch (o) {
      g.__e(o, e);
    }
    n.base = n.__P = null;
  }
  if (n = t.__k) for (i = 0; i < n.length; i++) n[i] && De(n[i], e, r || typeof t.type != "function");
  r || ie(t.__e), t.__c = t.__ = t.__e = void 0;
}
function Xe(t, e, r) {
  return this.constructor(t, r);
}
function Ke(t, e, r) {
  var n, i, o, s;
  e == document && (e = document.documentElement), g.__ && g.__(t, e), i = (n = !1) ? null : e.__k, o = [], s = [], le(e, t = e.__k = He(X, null, [t]), i || U, U, e.namespaceURI, i ? null : e.firstChild ? B.call(e.childNodes) : null, o, i ? i.__e : e.firstChild, n, s), Fe(o, t, s);
}
B = I.slice, g = { __e: function(t, e, r, n) {
  for (var i, o, s; e = e.__; ) if ((i = e.__c) && !i.__) try {
    if ((o = i.constructor) && o.getDerivedStateFromError != null && (i.setState(o.getDerivedStateFromError(t)), s = i.__d), i.componentDidCatch != null && (i.componentDidCatch(t, n || {}), s = i.__d), s) return i.__E = i;
  } catch (_) {
    t = _;
  }
  throw t;
} }, Pe = 0, T.prototype.setState = function(t, e) {
  var r;
  r = this.__s != null && this.__s != this.state ? this.__s : this.__s = $({}, this.state), typeof t == "function" && (t = t($({}, r), this.props)), t && $(r, t), t != null && this.__v && (e && this._sb.push(e), de(this));
}, T.prototype.forceUpdate = function(t) {
  this.__v && (this.__e = !0, t && this.__h.push(t), de(this));
}, T.prototype.render = X, S = [], Se = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, Me = function(t, e) {
  return t.__v.__b - e.__v.__b;
}, R.__r = 0, J = Math.random().toString(8), E = "__d" + J, A = "__a" + J, ze = /(PointerCapture)$|Capture$/i, oe = 0, Y = pe(!1), ee = pe(!0);
var Ge = 0;
function c(t, e, r, n, i, o) {
  e || (e = {});
  var s, _, d = e;
  if ("ref" in d) for (_ in d = {}, e) _ == "ref" ? s = e[_] : d[_] = e[_];
  var a = { type: t, props: d, key: r, ref: s, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: --Ge, __i: -1, __u: 0, __source: i, __self: o };
  if (typeof t == "function" && (s = t.defaultProps)) for (_ in s) d[_] === void 0 && (d[_] = s[_]);
  return g.vnode && g.vnode(a), a;
}
function z(t, e) {
  const r = t.states[e];
  if (!r) return null;
  const n = Number(r.state);
  return Number.isFinite(n) ? n : null;
}
function ae(t) {
  return t == null ? "—" : Math.round(t).toLocaleString("fr-FR");
}
function O(t) {
  return t == null ? "—" : t.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}
const Je = 5e3;
function Qe({ hass: t }) {
  const e = z(t, "sensor.molini_solaire_production"), r = z(t, "sensor.molini_solaire_production_aujourd_hui"), n = z(t, "sensor.molini_solaire_production_totale"), i = e == null ? 0 : Math.min(100, Math.round(e / Je * 100));
  return /* @__PURE__ */ c("div", { class: "grid grid-cols-1 sm:grid-cols-[1.4fr_1fr_1fr] gap-3", children: [
    /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-4", children: [
      /* @__PURE__ */ c("div", { class: "text-sm text-moli-muted", children: "Production en ce moment" }),
      /* @__PURE__ */ c("div", { class: "text-3xl font-medium leading-tight", children: [
        ae(e),
        /* @__PURE__ */ c("span", { class: "text-sm text-moli-muted", children: " W" })
      ] }),
      /* @__PURE__ */ c("div", { class: "mt-2.5 h-1.5 rounded-full bg-moli-border overflow-hidden", children: /* @__PURE__ */ c("div", { class: "h-full rounded-full bg-solar", style: { width: `${i}%` } }) })
    ] }),
    /* @__PURE__ */ c(he, { label: "Aujourd'hui", value: O(r), unit: "kWh" }),
    /* @__PURE__ */ c(he, { label: "Depuis l'origine", value: O(n), unit: "kWh" })
  ] });
}
function he({ label: t, value: e, unit: r }) {
  return /* @__PURE__ */ c("div", { class: "rounded-lg bg-moli-surface border border-moli-border p-4", children: [
    /* @__PURE__ */ c("div", { class: "text-sm text-moli-muted", children: t }),
    /* @__PURE__ */ c("div", { class: "text-2xl font-medium", children: [
      e,
      /* @__PURE__ */ c("span", { class: "text-xs text-moli-muted", children: [
        " ",
        r
      ] })
    ] })
  ] });
}
const Q = /^(?<prefix>.+?)_pv(?<n>\d+)(?:_power)?$/;
function Ze(t) {
  var r;
  const e = {};
  for (const n of t) {
    if (!n.startsWith("sensor.")) continue;
    const i = Q.exec(n);
    i != null && i.groups && (e[r = i.groups.prefix] ?? (e[r] = [])).push(n);
  }
  for (const n of Object.keys(e))
    e[n].sort(
      (i, o) => Number(Q.exec(i).groups.n) - Number(Q.exec(o).groups.n)
    );
  return e;
}
function Ee(t) {
  const e = t.toLowerCase();
  return e.includes("izypower") || e.includes("micro");
}
function Ye(t, e) {
  return `${Ee(t) ? "Micro-onduleur" : "Onduleur"} ${e + 1}`;
}
function et(t) {
  const e = Ze(t), r = { micro: 0, string: 0 };
  return Object.keys(e).sort().map((n) => {
    const i = Ee(n) ? "micro" : "string", o = Ye(n, r[i]++);
    return {
      key: n,
      label: o,
      panels: e[n].map((s, _) => ({ name: `P${_ + 1}`, eid: s }))
    };
  });
}
const tt = 400;
function rt({ hass: t }) {
  const e = et(Object.keys(t.states));
  return e.length === 0 ? null : /* @__PURE__ */ c("div", { class: "grid grid-cols-1 md:grid-cols-2 gap-3", children: e.map((r) => /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-3.5", children: [
    /* @__PURE__ */ c("div", { class: "text-[13px] text-moli-muted mb-2.5", children: r.label }),
    /* @__PURE__ */ c("div", { class: "grid grid-cols-2 gap-2", children: r.panels.map((n) => {
      const i = z(t, n.eid), o = i == null ? 0 : Math.min(100, Math.round(i / tt * 100));
      return /* @__PURE__ */ c("div", { "data-panel-tile": !0, class: "rounded-lg bg-moli-surface2 p-2.5", children: [
        /* @__PURE__ */ c("div", { class: "text-xs text-moli-muted", children: n.name }),
        /* @__PURE__ */ c("div", { class: "text-[17px] font-medium", children: [
          ae(i),
          /* @__PURE__ */ c("span", { class: "text-[11px] text-moli-muted", children: " W" })
        ] }),
        /* @__PURE__ */ c("div", { class: "mt-1.5 h-1 rounded-full bg-moli-border overflow-hidden", children: /* @__PURE__ */ c(
          "div",
          {
            class: `h-full rounded-full ${o < 20 ? "bg-low" : "bg-solar"}`,
            style: { width: `${o}%` }
          }
        ) })
      ] }, n.eid);
    }) })
  ] }, r.key)) });
}
function nt({ hass: t }) {
  const e = z(t, "sensor.molini_index_hc"), r = z(t, "sensor.molini_index_hp");
  return /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border px-4", children: [
    /* @__PURE__ */ c(fe, { label: "Index heures creuses", value: O(e), unit: "kWh", border: !0 }),
    /* @__PURE__ */ c(fe, { label: "Index heures pleines", value: O(r), unit: "kWh" })
  ] });
}
function fe({
  label: t,
  value: e,
  unit: r,
  border: n
}) {
  return /* @__PURE__ */ c(
    "div",
    {
      class: `flex items-center justify-between py-2.5 ${n ? "border-b border-moli-border" : ""}`,
      children: [
        /* @__PURE__ */ c("span", { class: "text-sm text-moli-muted", children: t }),
        /* @__PURE__ */ c("span", { class: "text-[15px] font-medium", children: [
          e,
          " ",
          r
        ] })
      ]
    }
  );
}
const me = "sensor.molini_consommation_maison";
function ot({ hass: t }) {
  const e = t.states[me];
  return !e || e.state === "unavailable" || e.state === "unknown" ? null : /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-4", children: [
    /* @__PURE__ */ c("div", { class: "text-sm text-moli-muted", children: "Consommation maison" }),
    /* @__PURE__ */ c("div", { class: "text-2xl font-medium", children: [
      ae(z(t, me)),
      /* @__PURE__ */ c("span", { class: "text-xs text-moli-muted", children: " W" })
    ] })
  ] });
}
var q, b, Z, ge, re = 0, je = [], w = g, be = w.__b, we = w.__r, ve = w.diffed, xe = w.__c, ye = w.unmount, ke = w.__;
function Te(t, e) {
  w.__h && w.__h(b, t, re || e), re = 0;
  var r = b.__H || (b.__H = { __: [], __h: [] });
  return t >= r.__.length && r.__.push({}), r.__[t];
}
function it(t) {
  return re = 1, lt(Le, t);
}
function lt(t, e, r) {
  var n = Te(q++, 2);
  if (n.t = t, !n.__c && (n.__ = [Le(void 0, e), function(_) {
    var d = n.__N ? n.__N[0] : n.__[0], a = n.t(d, _);
    d !== a && (n.__N = [a, n.__[1]], n.__c.setState({}));
  }], n.__c = b, !b.__f)) {
    var i = function(_, d, a) {
      if (!n.__c.__H) return !0;
      var h = n.__c.__H.__.filter(function(u) {
        return u.__c;
      });
      if (h.every(function(u) {
        return !u.__N;
      })) return !o || o.call(this, _, d, a);
      var l = n.__c.props !== _;
      return h.some(function(u) {
        if (u.__N) {
          var p = u.__[0];
          u.__ = u.__N, u.__N = void 0, p !== u.__[0] && (l = !0);
        }
      }), o && o.call(this, _, d, a) || l;
    };
    b.__f = !0;
    var o = b.shouldComponentUpdate, s = b.componentWillUpdate;
    b.componentWillUpdate = function(_, d, a) {
      if (this.__e) {
        var h = o;
        o = void 0, i(_, d, a), o = h;
      }
      s && s.call(this, _, d, a);
    }, b.shouldComponentUpdate = i;
  }
  return n.__N || n.__;
}
function st(t, e) {
  var r = Te(q++, 3);
  !w.__s && ct(r.__H, e) && (r.__ = t, r.u = e, b.__H.__h.push(r));
}
function at() {
  for (var t; t = je.shift(); ) {
    var e = t.__H;
    if (t.__P && e) try {
      e.__h.some(L), e.__h.some(ne), e.__h = [];
    } catch (r) {
      e.__h = [], w.__e(r, t.__v);
    }
  }
}
w.__b = function(t) {
  b = null, be && be(t);
}, w.__ = function(t, e) {
  t && e.__k && e.__k.__m && (t.__m = e.__k.__m), ke && ke(t, e);
}, w.__r = function(t) {
  we && we(t), q = 0;
  var e = (b = t.__c).__H;
  e && (Z === b ? (e.__h = [], b.__h = [], e.__.some(function(r) {
    r.__N && (r.__ = r.__N), r.u = r.__N = void 0;
  })) : (e.__h.some(L), e.__h.some(ne), e.__h = [], q = 0)), Z = b;
}, w.diffed = function(t) {
  ve && ve(t);
  var e = t.__c;
  e && e.__H && (e.__H.__h.length && (je.push(e) !== 1 && ge === w.requestAnimationFrame || ((ge = w.requestAnimationFrame) || _t)(at)), e.__H.__.some(function(r) {
    r.u && (r.__H = r.u), r.u = void 0;
  })), Z = b = null;
}, w.__c = function(t, e) {
  e.some(function(r) {
    try {
      r.__h.some(L), r.__h = r.__h.filter(function(n) {
        return !n.__ || ne(n);
      });
    } catch (n) {
      e.some(function(i) {
        i.__h && (i.__h = []);
      }), e = [], w.__e(n, r.__v);
    }
  }), xe && xe(t, e);
}, w.unmount = function(t) {
  ye && ye(t);
  var e, r = t.__c;
  r && r.__H && (r.__H.__.some(function(n) {
    try {
      L(n);
    } catch (i) {
      e = i;
    }
  }), r.__H = void 0, e && w.__e(e, r.__v));
};
var $e = typeof requestAnimationFrame == "function";
function _t(t) {
  var e, r = function() {
    clearTimeout(n), $e && cancelAnimationFrame(e), setTimeout(t);
  }, n = setTimeout(r, 35);
  $e && (e = requestAnimationFrame(r));
}
function L(t) {
  var e = b, r = t.__c;
  typeof r == "function" && (t.__c = void 0, r()), b = e;
}
function ne(t) {
  var e = b;
  t.__c = t.__(), b = e;
}
function ct(t, e) {
  return !t || t.length !== e.length || e.some(function(r, n) {
    return r !== t[n];
  });
}
function Le(t, e) {
  return typeof e == "function" ? e(t) : e;
}
async function dt(t, e, r = 24) {
  if (t.callWS)
    try {
      const n = /* @__PURE__ */ new Date(), i = new Date(n.getTime() - r * 36e5), o = await t.callWS({
        type: "history/history_during_period",
        start_time: i.toISOString(),
        end_time: n.toISOString(),
        entity_ids: [e],
        minimal_response: !0,
        no_attributes: !0
      }), s = o == null ? void 0 : o[e];
      if (Array.isArray(s) && s.length) {
        const _ = s.map((d) => ({
          t: d.lu != null ? d.lu * 1e3 : Date.parse(d.last_updated ?? d.last_changed ?? ""),
          v: Number(d.s ?? d.state)
        })).filter((d) => Number.isFinite(d.v) && Number.isFinite(d.t));
        if (_.length >= 2) return _;
      }
    } catch {
    }
  return ut(r);
}
function ut(t) {
  const e = [], r = Date.now();
  for (let n = t * 4; n >= 0; n--) {
    const i = r - n * 15 * 6e4, o = new Date(i), s = o.getHours() + o.getMinutes() / 60, _ = Math.exp(-Math.pow((s - 13) / 3.2, 2)) * 4600 - 60;
    e.push({ t: i, v: Math.max(0, Math.round(_)) });
  }
  return e;
}
function pt({ hass: t }) {
  const [e, r] = it([]);
  return st(() => {
    let n = !0;
    return dt(t, "sensor.molini_solaire_production", 24).then((i) => {
      n && r(i);
    }), () => {
      n = !1;
    };
  }, []), /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-4", children: e.length < 2 ? /* @__PURE__ */ c("div", { class: "h-40 flex items-center justify-center text-moli-muted text-sm", children: "Pas encore de données" }) : /* @__PURE__ */ c(ht, { points: e }) });
}
function ht({ points: t }) {
  const i = t.map((u) => u.t), o = Math.min(...i), s = Math.max(...i), _ = Math.max(100, ...t.map((u) => u.v)), d = (u) => 4 + (u - o) / (s - o || 1) * (720 - 2 * 4), a = (u) => 156 - u / _ * (160 - 2 * 4), h = t.map((u, p) => `${p ? "L" : "M"}${d(u.t).toFixed(1)},${a(u.v).toFixed(1)}`).join(" "), l = `${h} L${d(s).toFixed(1)},${156 .toFixed(1)} L${d(o).toFixed(1)},${156 .toFixed(1)} Z`;
  return /* @__PURE__ */ c(
    "svg",
    {
      viewBox: "0 0 720 160",
      class: "w-full h-40",
      preserveAspectRatio: "none",
      role: "img",
      "aria-label": "Production solaire des dernières 24 heures",
      children: [
        /* @__PURE__ */ c("path", { d: l, fill: "#1d9e75", "fill-opacity": "0.15" }),
        /* @__PURE__ */ c(
          "path",
          {
            d: h,
            fill: "none",
            stroke: "#1d9e75",
            "stroke-width": "2",
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
            "vector-effect": "non-scaling-stroke"
          }
        )
      ]
    }
  );
}
function D({ children: t }) {
  return /* @__PURE__ */ c("h2", { class: "text-base font-medium mb-3.5", children: t });
}
function ft({ hass: t }) {
  return /* @__PURE__ */ c("div", { class: "min-h-screen bg-moli-bg text-moli-text", children: /* @__PURE__ */ c("div", { class: "mx-auto max-w-5xl px-4 py-6 space-y-7", children: [
    /* @__PURE__ */ c("section", { children: [
      /* @__PURE__ */ c(D, { children: "Production solaire" }),
      /* @__PURE__ */ c(Qe, { hass: t })
    ] }),
    /* @__PURE__ */ c("section", { children: [
      /* @__PURE__ */ c(D, { children: "Production par panneau" }),
      /* @__PURE__ */ c(rt, { hass: t })
    ] }),
    /* @__PURE__ */ c("section", { children: [
      /* @__PURE__ */ c(D, { children: "Production des dernières 24 h" }),
      /* @__PURE__ */ c(pt, { hass: t })
    ] }),
    /* @__PURE__ */ c("section", { children: [
      /* @__PURE__ */ c(D, { children: "Compteur électrique" }),
      /* @__PURE__ */ c("div", { class: "grid grid-cols-1 sm:grid-cols-2 gap-3", children: [
        /* @__PURE__ */ c(nt, { hass: t }),
        /* @__PURE__ */ c(ot, { hass: t })
      ] })
    ] })
  ] }) });
}
function mt({ hass: t }) {
  return /* @__PURE__ */ c(ft, { hass: t });
}
const gt = '*,:before,:after{--tw-border-spacing-x: 0;--tw-border-spacing-y: 0;--tw-translate-x: 0;--tw-translate-y: 0;--tw-rotate: 0;--tw-skew-x: 0;--tw-skew-y: 0;--tw-scale-x: 1;--tw-scale-y: 1;--tw-pan-x: ;--tw-pan-y: ;--tw-pinch-zoom: ;--tw-scroll-snap-strictness: proximity;--tw-gradient-from-position: ;--tw-gradient-via-position: ;--tw-gradient-to-position: ;--tw-ordinal: ;--tw-slashed-zero: ;--tw-numeric-figure: ;--tw-numeric-spacing: ;--tw-numeric-fraction: ;--tw-ring-inset: ;--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-color: rgb(59 130 246 / .5);--tw-ring-offset-shadow: 0 0 #0000;--tw-ring-shadow: 0 0 #0000;--tw-shadow: 0 0 #0000;--tw-shadow-colored: 0 0 #0000;--tw-blur: ;--tw-brightness: ;--tw-contrast: ;--tw-grayscale: ;--tw-hue-rotate: ;--tw-invert: ;--tw-saturate: ;--tw-sepia: ;--tw-drop-shadow: ;--tw-backdrop-blur: ;--tw-backdrop-brightness: ;--tw-backdrop-contrast: ;--tw-backdrop-grayscale: ;--tw-backdrop-hue-rotate: ;--tw-backdrop-invert: ;--tw-backdrop-opacity: ;--tw-backdrop-saturate: ;--tw-backdrop-sepia: ;--tw-contain-size: ;--tw-contain-layout: ;--tw-contain-paint: ;--tw-contain-style: }::backdrop{--tw-border-spacing-x: 0;--tw-border-spacing-y: 0;--tw-translate-x: 0;--tw-translate-y: 0;--tw-rotate: 0;--tw-skew-x: 0;--tw-skew-y: 0;--tw-scale-x: 1;--tw-scale-y: 1;--tw-pan-x: ;--tw-pan-y: ;--tw-pinch-zoom: ;--tw-scroll-snap-strictness: proximity;--tw-gradient-from-position: ;--tw-gradient-via-position: ;--tw-gradient-to-position: ;--tw-ordinal: ;--tw-slashed-zero: ;--tw-numeric-figure: ;--tw-numeric-spacing: ;--tw-numeric-fraction: ;--tw-ring-inset: ;--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-color: rgb(59 130 246 / .5);--tw-ring-offset-shadow: 0 0 #0000;--tw-ring-shadow: 0 0 #0000;--tw-shadow: 0 0 #0000;--tw-shadow-colored: 0 0 #0000;--tw-blur: ;--tw-brightness: ;--tw-contrast: ;--tw-grayscale: ;--tw-hue-rotate: ;--tw-invert: ;--tw-saturate: ;--tw-sepia: ;--tw-drop-shadow: ;--tw-backdrop-blur: ;--tw-backdrop-brightness: ;--tw-backdrop-contrast: ;--tw-backdrop-grayscale: ;--tw-backdrop-hue-rotate: ;--tw-backdrop-invert: ;--tw-backdrop-opacity: ;--tw-backdrop-saturate: ;--tw-backdrop-sepia: ;--tw-contain-size: ;--tw-contain-layout: ;--tw-contain-paint: ;--tw-contain-style: }*,:before,:after{box-sizing:border-box;border-width:0;border-style:solid;border-color:#e5e7eb}:before,:after{--tw-content: ""}html,:host{line-height:1.5;-webkit-text-size-adjust:100%;-moz-tab-size:4;-o-tab-size:4;tab-size:4;font-family:ui-sans-serif,system-ui,sans-serif,"Apple Color Emoji","Segoe UI Emoji",Segoe UI Symbol,"Noto Color Emoji";font-feature-settings:normal;font-variation-settings:normal;-webkit-tap-highlight-color:transparent}body{margin:0;line-height:inherit}hr{height:0;color:inherit;border-top-width:1px}abbr:where([title]){-webkit-text-decoration:underline dotted;text-decoration:underline dotted}h1,h2,h3,h4,h5,h6{font-size:inherit;font-weight:inherit}a{color:inherit;text-decoration:inherit}b,strong{font-weight:bolder}code,kbd,samp,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,monospace;font-feature-settings:normal;font-variation-settings:normal;font-size:1em}small{font-size:80%}sub,sup{font-size:75%;line-height:0;position:relative;vertical-align:baseline}sub{bottom:-.25em}sup{top:-.5em}table{text-indent:0;border-color:inherit;border-collapse:collapse}button,input,optgroup,select,textarea{font-family:inherit;font-feature-settings:inherit;font-variation-settings:inherit;font-size:100%;font-weight:inherit;line-height:inherit;letter-spacing:inherit;color:inherit;margin:0;padding:0}button,select{text-transform:none}button,input:where([type=button]),input:where([type=reset]),input:where([type=submit]){-webkit-appearance:button;background-color:transparent;background-image:none}:-moz-focusring{outline:auto}:-moz-ui-invalid{box-shadow:none}progress{vertical-align:baseline}::-webkit-inner-spin-button,::-webkit-outer-spin-button{height:auto}[type=search]{-webkit-appearance:textfield;outline-offset:-2px}::-webkit-search-decoration{-webkit-appearance:none}::-webkit-file-upload-button{-webkit-appearance:button;font:inherit}summary{display:list-item}blockquote,dl,dd,h1,h2,h3,h4,h5,h6,hr,figure,p,pre{margin:0}fieldset{margin:0;padding:0}legend{padding:0}ol,ul,menu{list-style:none;margin:0;padding:0}dialog{padding:0}textarea{resize:vertical}input::-moz-placeholder,textarea::-moz-placeholder{opacity:1;color:#9ca3af}input::placeholder,textarea::placeholder{opacity:1;color:#9ca3af}button,[role=button]{cursor:pointer}:disabled{cursor:default}img,svg,video,canvas,audio,iframe,embed,object{display:block;vertical-align:middle}img,video{max-width:100%;height:auto}[hidden]:where(:not([hidden=until-found])){display:none}.visible{visibility:visible}.mx-auto{margin-left:auto;margin-right:auto}.mb-2\\.5{margin-bottom:.625rem}.mb-3\\.5{margin-bottom:.875rem}.mt-1\\.5{margin-top:.375rem}.mt-2\\.5{margin-top:.625rem}.inline{display:inline}.flex{display:flex}.grid{display:grid}.h-1{height:.25rem}.h-1\\.5{height:.375rem}.h-40{height:10rem}.h-full{height:100%}.min-h-screen{min-height:100vh}.w-full{width:100%}.max-w-5xl{max-width:64rem}.grid-cols-1{grid-template-columns:repeat(1,minmax(0,1fr))}.grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.items-center{align-items:center}.justify-center{justify-content:center}.justify-between{justify-content:space-between}.gap-2{gap:.5rem}.gap-3{gap:.75rem}.space-y-7>:not([hidden])~:not([hidden]){--tw-space-y-reverse: 0;margin-top:calc(1.75rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1.75rem * var(--tw-space-y-reverse))}.overflow-hidden{overflow:hidden}.rounded-full{border-radius:9999px}.rounded-lg{border-radius:.5rem}.rounded-xl{border-radius:.75rem}.border{border-width:1px}.border-b{border-bottom-width:1px}.border-moli-border{--tw-border-opacity: 1;border-color:rgb(42 49 61 / var(--tw-border-opacity, 1))}.bg-low{--tw-bg-opacity: 1;background-color:rgb(186 117 23 / var(--tw-bg-opacity, 1))}.bg-moli-bg{--tw-bg-opacity: 1;background-color:rgb(15 17 21 / var(--tw-bg-opacity, 1))}.bg-moli-border{--tw-bg-opacity: 1;background-color:rgb(42 49 61 / var(--tw-bg-opacity, 1))}.bg-moli-surface{--tw-bg-opacity: 1;background-color:rgb(23 26 33 / var(--tw-bg-opacity, 1))}.bg-moli-surface2{--tw-bg-opacity: 1;background-color:rgb(31 36 46 / var(--tw-bg-opacity, 1))}.bg-solar{--tw-bg-opacity: 1;background-color:rgb(29 158 117 / var(--tw-bg-opacity, 1))}.p-2\\.5{padding:.625rem}.p-3\\.5{padding:.875rem}.p-4{padding:1rem}.px-4{padding-left:1rem;padding-right:1rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}.py-6{padding-top:1.5rem;padding-bottom:1.5rem}.text-2xl{font-size:1.5rem;line-height:2rem}.text-3xl{font-size:1.875rem;line-height:2.25rem}.text-\\[11px\\]{font-size:11px}.text-\\[13px\\]{font-size:13px}.text-\\[15px\\]{font-size:15px}.text-\\[17px\\]{font-size:17px}.text-base{font-size:1rem;line-height:1.5rem}.text-sm{font-size:.875rem;line-height:1.25rem}.text-xs{font-size:.75rem;line-height:1rem}.font-medium{font-weight:500}.leading-tight{line-height:1.25}.text-moli-muted{--tw-text-opacity: 1;color:rgb(154 163 178 / var(--tw-text-opacity, 1))}.text-moli-text{--tw-text-opacity: 1;color:rgb(230 233 239 / var(--tw-text-opacity, 1))}.shadow{--tw-shadow: 0 1px 3px 0 rgb(0 0 0 / .1), 0 1px 2px -1px rgb(0 0 0 / .1);--tw-shadow-colored: 0 1px 3px 0 var(--tw-shadow-color), 0 1px 2px -1px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow, 0 0 #0000),var(--tw-ring-shadow, 0 0 #0000),var(--tw-shadow)}.filter{filter:var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow)}@media (min-width: 640px){.sm\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.sm\\:grid-cols-\\[1\\.4fr_1fr_1fr\\]{grid-template-columns:1.4fr 1fr 1fr}}@media (min-width: 768px){.md\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}}';
class bt extends HTMLElement {
  constructor() {
    super();
    G(this, "_hass", null);
    G(this, "mountPoint");
    const r = this.attachShadow({ mode: "open" }), n = document.createElement("style");
    n.textContent = gt, r.appendChild(n), this.mountPoint = document.createElement("div"), r.appendChild(this.mountPoint);
  }
  set hass(r) {
    this._hass = r, this.renderApp();
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    this.renderApp();
  }
  renderApp() {
    Ke(He(mt, { hass: this._hass ?? { states: {} } }), this.mountPoint);
  }
}
customElements.get("moli-panel") || customElements.define("moli-panel", bt);
